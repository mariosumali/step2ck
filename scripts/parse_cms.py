#!/usr/bin/env python3
"""
CMS PDF Question Parser

Parses USMLE Step 2 CK CMS PDFs into structured JSON with validation and reporting.
Supports three PDF types: official NBME (text-extractable), official NBME (image-only),
and community answer keys.
"""

import json
import os
import re
import sys
import argparse
import time
import base64
import io
import random
from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import defaultdict

import pypdf

try:
    import fitz  # pymupdf — used for page-to-image conversion
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

SECTION_CODES = {
    "1 Internal Medicine": "IM",
    "2 Surgery": "SURG",
    "3 OBGYN": "OB",
    "4 Pediatrics": "PEDS",
    "5 Neurology": "NEURO",
    "6 Psychiatry": "PSYCH",
    "7 Family Medicine": "FM",
    "8 Emergency Medicine": "EM",
    "Sample Items": "SAMPLE",
}

SECTION_SLUGS = {
    "1 Internal Medicine": "1_internal_medicine",
    "2 Surgery": "2_surgery",
    "3 OBGYN": "3_obgyn",
    "4 Pediatrics": "4_pediatrics",
    "5 Neurology": "5_neurology",
    "6 Psychiatry": "6_psychiatry",
    "7 Family Medicine": "7_family_medicine",
    "8 Emergency Medicine": "8_emergency_medicine",
    "Sample Items": "sample_items",
}

# OCR artifact corrections for system names in the table of contents
SYSTEM_NAME_FIXES = {
    "SY.stems": "Systems",
    "SP-ecial": "Special",
    "LY.mP-horeticular": "Lymphoreticular",
    "ResP-iratorY.": "Respiratory",
    "UrinarY.": "Urinary",
    "ReP-roductive": "Reproductive",
    "MultisY.stem": "Multisystem",
    "MQal": "Moral",
    "EP-idemiologY.": "Epidemiology",
    "P-hysical": "Physical",
}

IMAGE_PATTERN = re.compile(
    r'\b(?:is\s+shown|are\s+shown|shown\s+here|shown\s+in\s+the|'
    r'photograph|photomicrograph|gross\s+appearance|'
    r'x-ray\s+of|x-ray\s+is|radiograph|CT\s+scan|CT\s+of|'
    r'MRI\s+of|MRI\s+is|ultrasound|ultrasonograph|echocardiogram|'
    r'biopsy\s+specimen|microscopic\s+image|histologic|'
    r'the\s+image|the\s+figure|the\s+slide|the\s+picture)\b',
    re.IGNORECASE,
)

TRUNCATION_ENDING = re.compile(
    r'(?:\s+(?:and|or|but|the|a|an|in|of|to|for|with|from|by|at|on|'
    r'is|are|was|were|that|this|which|as|it|its|their|his|her)\s*'
    r'|,\s*|;\s*|\(\s*|\[\s*|"\s*)$'
)

# PDF type tags
OFFICIAL_TEXT = "official_text"
OFFICIAL_IMAGE = "official_image"
COMMUNITY = "community"
Q_ONLY = "q_only"


# ═══════════════════════════════════════════════════════════════════════════════
# Utility functions
# ═══════════════════════════════════════════════════════════════════════════════

def clean_text(text: str) -> str:
    """Normalize whitespace, strip trailing UI chrome and watermarks."""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(
        r'[\s,]*(?:Previous\s*)?(?:Next\s*)?(?:Score Report\s*)?'
        r'(?:Lab Values\s*)?(?:Calculator\s*)?(?:Help\s*)?(?:Pause\s*)?'
        r'(?:https?://t\.me/\S+\s*)*$',
        '', text,
    ).strip()
    # Remove stray OCR artifacts at the very end (e.g., ", ~ r-- r ,")
    text = re.sub(r'[\s,~\u25a0\u2713r\u201c\u201d\'"F\-]+$', '', text).strip()
    # Ensure we didn't strip a valid trailing period
    if text and text[-1] not in '.?!)\'"':
        pass  # leave as-is; validation will flag it
    return text


def extract_full_text(pdf_path: Path) -> str:
    """Extract all text from a PDF via pypdf."""
    reader = pypdf.PdfReader(str(pdf_path))
    parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Discovery & Classification
# ═══════════════════════════════════════════════════════════════════════════════

def discover_pdfs(cms_dir: Path) -> list[dict]:
    """Walk CMS directory tree and classify every PDF set."""
    results = []

    for section_dir in sorted(cms_dir.iterdir()):
        if not section_dir.is_dir() or section_dir.name.startswith('.'):
            continue

        section_name = section_dir.name
        a_pdfs: dict[str, Path] = {}
        q_pdfs: dict[str, Path] = {}

        for f in section_dir.iterdir():
            if f.suffix.lower() != '.pdf':
                continue
            a_match = re.match(r'^(\d+)A\.pdf$', f.name)
            q_match = re.match(r'^(\d+)\s*Q\.pdf$', f.name)
            if a_match:
                a_pdfs[a_match.group(1)] = f
            elif q_match:
                q_pdfs[q_match.group(1)] = f

        all_nums = sorted(set(list(a_pdfs.keys()) + list(q_pdfs.keys())), key=int)

        for num in all_nums:
            a_pdf = a_pdfs.get(num)
            q_pdf = q_pdfs.get(num)
            pdf_type = classify_a_pdf(a_pdf) if a_pdf else Q_ONLY

            results.append({
                "section": section_name,
                "number": num,
                "a_pdf": a_pdf,
                "q_pdf": q_pdf,
                "type": pdf_type,
            })

    return results


def classify_a_pdf(pdf_path: Path) -> str:
    """Classify an A PDF by examining its text content."""
    try:
        reader = pypdf.PdfReader(str(pdf_path))
    except Exception:
        return OFFICIAL_IMAGE  # unreadable → treat as image

    text = ""
    for page in reader.pages[:5]:
        try:
            t = page.extract_text()
            if t:
                text += t
        except Exception:
            continue

    if "Exam Section" in text:
        return OFFICIAL_TEXT

    clean = re.sub(r'https?://t\.me/\S+', '', text).strip()
    if not clean:
        return OFFICIAL_IMAGE

    return COMMUNITY


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2A: Official NBME Text Parser
# ═══════════════════════════════════════════════════════════════════════════════

def parse_system_toc(text: str) -> dict[int, str]:
    """Parse table of contents → {question_number: system_name}."""
    mapping: dict[int, str] = {}
    toc_pattern = r'SY\.?stem:?\s*([^:]+):\s*([\d,\s]+)'
    matches = re.findall(toc_pattern, text, re.IGNORECASE)

    for raw_name, numbers_str in matches:
        name = raw_name.strip()
        for wrong, right in SYSTEM_NAME_FIXES.items():
            name = name.replace(wrong, right)
        name = re.sub(r'\s+', ' ', name).strip()

        for n in re.findall(r'\d+', numbers_str):
            mapping[int(n)] = name

    return mapping


def extract_stem(chunk: str) -> Optional[str]:
    """Extract question stem from a chunk of text for one question."""
    # The stem sits between the question number (e.g., "~ 11 . A previously…")
    # and the first answer choice line (e.g., "\nA) …").
    # OCR artifacts: extra spaces around the period, various prefix chars.
    patterns = [
        # After "Self-Assessment" marker
        r"Self-Assessment\s*\n?[^\d]*?(\d+)\s*\.\s*(.*?)(?=\n\s*[A-L]\s*[)\}])",
        # After common OCR prefix chars (■ ~ X ' etc.)
        r"['\"\u2018\u2019~\u2713\u25A0XI]+\s*(\d+)\s*\.\s*(.*?)(?=\n\s*[A-L]\s*[)\}])",
        # Plain "N. Text" (most flexible)
        r"\n\s*(\d+)\s*\.\s+([A-Z].*?)(?=\n\s*[A-L]\s*[)\}])",
        # Fallback: find "N. Text" before "Correct Answer" if choices aren't detected
        r"\n\s*(\d+)\s*\.\s+([A-Z].*?)(?=Correct\s*Answer)",
    ]
    for pat in patterns:
        m = re.search(pat, chunk, re.DOTALL)
        if m:
            return clean_text(m.group(2))
    return None


def extract_choices(chunk: str) -> dict[str, str]:
    """Extract answer choices {letter: text} from a question chunk."""
    choices: dict[str, str] = {}

    # Stop collecting once we hit the explanation section
    cutoff = re.search(r'Correct\s*Answer\s*:', chunk, re.IGNORECASE)
    choice_region = chunk[:cutoff.start()] if cutoff else chunk

    for line in choice_region.split('\n'):
        stripped = line.strip()

        # Two-column layout: "A) text     G) text" (2+ spaces between columns)
        two = re.match(
            r'([A-L])\s*[)\}]\s*(.+?)\s{2,}([A-L])\s*[)\}]\s*(.+?)$', stripped
        )
        if two:
            choices[two.group(1)] = clean_text(two.group(2))
            choices[two.group(3)] = clean_text(two.group(4))
            continue

        # Single column: "A) text" or "A} text"
        one = re.match(r'([A-L])\s*[)\}]\s*(.+?)$', stripped)
        if one:
            letter, text = one.group(1), one.group(2)
            if 'Choice' not in text:
                choices[letter] = clean_text(text)

    return choices


def extract_correct_answer(chunk: str) -> Optional[str]:
    """Find the correct answer letter in a question chunk."""
    # "Correct Answer: E." or "CorrectAnswer: E." (no space — OCR variant)
    m = re.search(r'Correct\s*Answer\s*:\s*([A-L])\.?\s', chunk, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # Parenthetical: "(E) The/For/This/In…" — explanation-style answer indicator.
    # Only match AFTER the choices section to avoid false positives inside stems.
    last_choice = None
    for cm in re.finditer(r'\n\s*[A-L]\s*[)\}]', chunk):
        last_choice = cm.end()
    search_region = chunk[last_choice:] if last_choice else chunk

    m = re.search(
        r'\(([A-L])\)\s*(?:For|The|This|In|A\s|An\s|If|When|Because|Since|As\s|Any\s)',
        search_region,
    )
    if m:
        return m.group(1).upper()

    # "(E is correct)"
    m = re.search(r'\(([A-L])\s+is\s+correct\)', chunk, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def extract_explanations(
    chunk: str, correct_answer: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """Extract correct and incorrect explanations."""
    correct_expl = None
    incorrect_expl = None

    # ── Format 1: "Correct Answer: X.  explanation … Incorrect Answers: …" ──
    m = re.search(
        r'Correct\s*Answer\s*:\s*[A-L]\.?\s*(.*?)'
        r'(?=Incorrect\s*Answers?:|lncorrect\s*Answers?:|$)',
        chunk, re.DOTALL | re.IGNORECASE,
    )
    if m:
        correct_expl = clean_text(m.group(1)) or None

    m = re.search(
        r'(?:Incorrect|lncorrect)\s*Answers?:\s*'
        r'[A-L](?:,\s*[A-L])*(?:,?\s*and\s*[A-L])?\.?\s*'
        r'(.*?)(?=Exam Section|Next Score Report|https://|$)',
        chunk, re.DOTALL | re.IGNORECASE,
    )
    if m:
        incorrect_expl = clean_text(m.group(1)) or None

    # ── Format 2: parenthetical — "(C) explanation … (D, E) why wrong …" ──
    # Used when there is no "Correct Answer:" header.
    if not correct_expl and correct_answer:
        paren_m = re.search(
            rf'\({correct_answer}\)\s*(.*?)(?=Exam Section|Next Score Report|https://|$)',
            chunk, re.DOTALL,
        )
        if paren_m:
            full_block = paren_m.group(1)

            # Split at the first "(OTHER_LETTER)" to separate correct from incorrect
            other_m = re.search(
                r'\([A-L](?:,\s*[A-L])*\)\s',
                full_block,
            )
            if other_m:
                correct_expl = clean_text(full_block[:other_m.start()]) or None
                incorrect_expl = clean_text(full_block[other_m.start():]) or None
            else:
                correct_expl = clean_text(full_block) or None

    return correct_expl, incorrect_expl


def try_recover_missing_choice(
    chunk: str, choices: dict[str, str], correct_answer: str
) -> dict[str, str]:
    """When the correct answer letter is missing from choices, try to recover it."""
    if correct_answer in choices:
        return choices

    # Look for "LETTER text" without parenthesis near "Correct Answer"
    pat = rf'\n\s*{correct_answer}\s+([A-Z][^\n]+?)\s*\n.*?Correct\s*Answer'
    m = re.search(pat, chunk, re.DOTALL | re.IGNORECASE)
    if m:
        choices[correct_answer] = clean_text(m.group(1))
        return choices

    # Look for text right before "Correct Answer: X" that looks like a choice
    pat = rf'\n([^\n]+?)\s*\nCorrect\s*Answer\s*:\s*{correct_answer}'
    m = re.search(pat, chunk)
    if m:
        text = m.group(1).strip()
        text = re.sub(r'^[a-z]{2,5}\s*', '', text)  # remove OCR junk prefix
        text = re.sub(rf'^{correct_answer}\s+', '', text)
        if text and not re.match(r'^[A-L][)\}}]', text):
            choices[correct_answer] = clean_text(text)

    return choices


def merge_same_item_chunks(chunks: list[str]) -> list[str]:
    """Merge consecutive chunks that belong to the same Item number.

    Multi-page questions repeat the 'Exam Section : Item N of M' header on each
    page, producing multiple chunks for one question.  We concatenate them so
    each question is represented by exactly one (merged) chunk.
    """
    merged: dict[int, str] = {}
    order: list[int] = []

    for chunk in chunks:
        m = re.search(r'Item\s+(\d+)\s+of\s+(\d+)', chunk)
        if not m:
            continue
        q_num = int(m.group(1))
        if q_num in merged:
            merged[q_num] += "\n" + chunk
        else:
            merged[q_num] = chunk
            order.append(q_num)

    return [merged[n] for n in order]


def parse_official_text(pdf_path: Path, section_name: str, cms_number: str) -> list[dict]:
    """Parse an official NBME PDF that has extractable text."""
    full_text = extract_full_text(pdf_path)
    section_code = SECTION_CODES.get(section_name, "UNK")
    system_map = parse_system_toc(full_text)

    raw_chunks = re.split(r'(?=Exam Section\s*:\s*Item\s+\d+\s+of\s+\d+)', full_text)
    chunks = merge_same_item_chunks(raw_chunks)
    questions = []

    for chunk in chunks:
        if not chunk.strip():
            continue

        item_m = re.search(r'Item\s+(\d+)\s+of\s+(\d+)', chunk)
        if not item_m:
            continue

        q_num = int(item_m.group(1))
        stem = extract_stem(chunk)
        choices = extract_choices(chunk)
        correct = extract_correct_answer(chunk)

        if correct and choices:
            choices = try_recover_missing_choice(chunk, choices, correct)

        correct_expl, incorrect_expl = extract_explanations(chunk, correct)
        has_image = detect_image(stem)

        questions.append({
            "questionNumber": q_num,
            "questionStem": stem,
            "choices": choices or None,
            "correctAnswer": correct,
            "correctExplanation": correct_expl,
            "incorrectExplanation": incorrect_expl,
            "image": has_image,
            "id": f"{section_code}-{cms_number}-{q_num}",
            "section": section_code,
            "subsection": f"CMS-{cms_number}",
            "system": system_map.get(q_num),
        })

    return questions


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2C: Community PDF Parser
# ═══════════════════════════════════════════════════════════════════════════════

def parse_community_pdf(pdf_path: Path, section_name: str, cms_number: str) -> list[dict]:
    """Parse a community-written answer key PDF."""
    full_text = extract_full_text(pdf_path)
    section_code = SECTION_CODES.get(section_name, "UNK")

    # Split on lines that start with a number + punctuation + letter (next question)
    block_starts = list(re.finditer(r'(?:^|\n)\s*(\d+)\s*[.)\-:]\s*([A-La-l])', full_text))

    questions = []
    for i, m in enumerate(block_starts):
        q_num = int(m.group(1))
        answer = m.group(2).upper()

        # Slice text from this match to the next
        start = m.end()
        end = block_starts[i + 1].start() if i + 1 < len(block_starts) else len(full_text)
        body = full_text[start:end].strip()

        # Clean common separators at start
        body = re.sub(r'^[.)\-:•\s]+', '', body).strip()

        # Attempt to split correct vs incorrect explanation
        wrong_m = re.search(
            r'(?:[A-L]\s+is\s+wrong|Incorrect|Wrong\s+answer)',
            body, re.IGNORECASE,
        )
        if wrong_m:
            correct_expl = clean_text(body[:wrong_m.start()])
            incorrect_expl = clean_text(body[wrong_m.start():])
        else:
            correct_expl = clean_text(body)
            incorrect_expl = None

        questions.append({
            "questionNumber": q_num,
            "questionStem": None,
            "choices": None,
            "correctAnswer": answer,
            "correctExplanation": correct_expl or None,
            "incorrectExplanation": incorrect_expl,
            "image": None,
            "id": f"{section_code}-{cms_number}-{q_num}",
            "section": section_code,
            "subsection": f"CMS-{cms_number}",
            "system": None,
        })

    return questions


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2B: Image-Only Handler — reuse existing output or call Vision AI
# ═══════════════════════════════════════════════════════════════════════════════

def import_existing_output(
    existing_dir: Path, section_name: str, cms_number: str
) -> Optional[list[dict]]:
    """Import questions from the previous run's output/ directory."""
    slug = SECTION_SLUGS.get(section_name, section_name.lower().replace(" ", "_"))

    for filename in [f"cms_{cms_number}.json", f"questions_{cms_number}A.pdf.json"]:
        path = existing_dir / slug / filename
        if path.exists():
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            if data:
                return data
    return None


def normalize_imported_question(q: dict, section_name: str, cms_number: str) -> dict:
    """Reshape an imported question to match our output schema."""
    section_code = SECTION_CODES.get(section_name, "UNK")
    q_num = q.get("questionNumber", 0)
    stem = q.get("questionStem")

    return {
        "questionNumber": q_num,
        "questionStem": stem,
        "choices": q.get("choices"),
        "correctAnswer": q.get("correctAnswer"),
        "correctExplanation": q.get("correctExplanation"),
        "incorrectExplanation": q.get("incorrectExplanation"),
        "image": detect_image(stem),
        "id": q.get("id", f"{section_code}-{cms_number}-{q_num}"),
        "section": section_code,
        "subsection": f"CMS-{cms_number}",
        "system": q.get("system"),
    }


# ── Vision AI (opt-in) ──────────────────────────────────────────────────────

def vision_call(client, prompt: str, image_b64: str, label: str,
                max_retries: int = 5) -> Optional[dict]:
    """Generic Vision API call with retry + exponential backoff."""
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high",
                        }},
                    ],
                }],
                max_tokens=2000,
                temperature=0,
            )
            body = resp.choices[0].message.content.strip()
            body = re.sub(r'^```(?:json)?\n?', '', body)
            body = re.sub(r'\n?```$', '', body)
            return json.loads(body)

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str:
                wait = (2 ** attempt) + random.random()
                print(f"      Rate limited ({label}, attempt {attempt+1}), "
                      f"waiting {wait:.1f}s...")
                time.sleep(wait)
            else:
                print(f"      Vision error ({label}): {e}")
                return None

    print(f"      Gave up on {label} after {max_retries} retries")
    return None


def vision_extract_page(client, image_b64: str, q_index: int, section_code: str,
                        cms_number: str, max_retries: int = 5) -> Optional[dict]:
    """Send one page image to GPT-4o and extract the question JSON."""
    prompt = (
        "Extract the USMLE question from this image. Return a JSON object with exactly "
        "these fields:\n"
        '{\n'
        '  "questionNumber": <int>,\n'
        '  "questionStem": "<full question text>",\n'
        '  "choices": {"A": "...", "B": "...", ...},\n'
        '  "correctAnswer": "<letter>",\n'
        '  "correctExplanation": "<explanation>",\n'
        '  "incorrectExplanation": "<explanation or null>",\n'
        '  "hasImage": <true if the page contains a clinical image/photo/x-ray, else false>\n'
        '}\n\n'
        'If this page is NOT a question (title page, TOC, etc.), return: {"skip": true}\n'
        'Return ONLY valid JSON, no markdown fences.'
    )

    data = vision_call(client, prompt, image_b64, f"page {q_index}", max_retries)
    if data and data.get("skip"):
        return None
    return data


def parse_with_vision(pdf_path: Path, section_name: str, cms_number: str,
                      client, max_workers: int = 2) -> list[dict]:
    """Parse an image-only PDF using GPT-4o Vision."""
    section_code = SECTION_CODES.get(section_name, "UNK")

    if FITZ_AVAILABLE:
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
    elif PDF2IMAGE_AVAILABLE:
        images = convert_from_path(str(pdf_path), dpi=150)
        page_count = len(images)
    else:
        print("    No PDF-to-image library available (need pymupdf or pdf2image)")
        return []

    print(f"    {page_count} pages to process via Vision AI...")
    questions = []

    for i in range(page_count):
        # Convert page to PNG base64
        if FITZ_AVAILABLE:
            pix = doc[i].get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
        else:
            buf = io.BytesIO()
            images[i].save(buf, format="PNG")
            img_bytes = buf.getvalue()

        img_b64 = base64.b64encode(img_bytes).decode()
        data = vision_extract_page(client, img_b64, i + 1, section_code, cms_number)

        if data:
            q_num = data.get("questionNumber", i + 1)
            has_img = True if data.get("hasImage") else None
            questions.append({
                "questionNumber": q_num,
                "questionStem": data.get("questionStem"),
                "choices": data.get("choices"),
                "correctAnswer": data.get("correctAnswer"),
                "correctExplanation": data.get("correctExplanation"),
                "incorrectExplanation": data.get("incorrectExplanation"),
                "image": has_img,
                "id": f"{section_code}-{cms_number}-{q_num}",
                "section": section_code,
                "subsection": f"CMS-{cms_number}",
                "system": None,
            })

        if (i + 1) % 10 == 0:
            print(f"      Progress: {i+1}/{page_count} pages")

    if FITZ_AVAILABLE:
        doc.close()

    questions.sort(key=lambda q: q.get("questionNumber", 0))
    return questions


def _pdf_page_to_b64(pdf_path: Path, page_idx: int) -> str:
    """Convert a single PDF page to a PNG base64 string."""
    if FITZ_AVAILABLE:
        doc = fitz.open(str(pdf_path))
        pix = doc[page_idx].get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        doc.close()
    elif PDF2IMAGE_AVAILABLE:
        images = convert_from_path(
            str(pdf_path), dpi=150, first_page=page_idx + 1, last_page=page_idx + 1,
        )
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")
        img_bytes = buf.getvalue()
    else:
        raise RuntimeError("No PDF-to-image library available")
    return base64.b64encode(img_bytes).decode()


Q_PDF_VISION_PROMPT = (
    "Extract the USMLE question from this image. This page contains ONLY the "
    "question — no answer or explanation. Return a JSON object:\n"
    '{\n'
    '  "questionNumber": <int>,\n'
    '  "questionStem": "<full question text>",\n'
    '  "choices": {"A": "...", "B": "...", ...},\n'
    '  "hasImage": <true if the page contains a clinical image/photo/x-ray, else false>\n'
    '}\n\n'
    'If this page is NOT a question (blank, title page, etc.), return: {"skip": true}\n'
    'Return ONLY valid JSON, no markdown fences.'
)


def parse_q_pdf_with_vision(q_pdf: Path, client) -> list[dict]:
    """Extract question stems + choices from an image-only Q PDF via Vision AI."""
    if FITZ_AVAILABLE:
        doc = fitz.open(str(q_pdf))
        page_count = len(doc)
        doc.close()
    elif PDF2IMAGE_AVAILABLE:
        from pdf2image.pdf2image import pdfinfo_from_path
        info = pdfinfo_from_path(str(q_pdf))
        page_count = info.get("Pages", 0)
    else:
        print("    No PDF-to-image library available")
        return []

    print(f"    Extracting stems from Q PDF ({page_count} pages)...")
    results = []

    for i in range(page_count):
        img_b64 = _pdf_page_to_b64(q_pdf, i)
        data = vision_call(client, Q_PDF_VISION_PROMPT, img_b64, f"Q-page {i+1}")

        if data and not data.get("skip"):
            results.append({
                "questionNumber": data.get("questionNumber", i + 1),
                "questionStem": data.get("questionStem"),
                "choices": data.get("choices"),
                "hasImage": data.get("hasImage", False),
            })

        if (i + 1) % 10 == 0:
            print(f"      Progress: {i+1}/{page_count} pages")

    print(f"      Got {len(results)} question stems from Q PDF")
    return results


def merge_community_with_q_data(
    answer_questions: list[dict], q_data: list[dict],
) -> list[dict]:
    """Merge community A-PDF answers with Q-PDF stems+choices by question number."""
    q_lookup: dict[int, dict] = {d["questionNumber"]: d for d in q_data}

    for q in answer_questions:
        qn = q["questionNumber"]
        if qn in q_lookup:
            src = q_lookup[qn]
            if not q.get("questionStem") and src.get("questionStem"):
                q["questionStem"] = src["questionStem"]
            if not q.get("choices") and src.get("choices"):
                q["choices"] = src["choices"]
            if src.get("hasImage"):
                q["image"] = True
            elif q["image"] is None and q.get("questionStem"):
                q["image"] = detect_image(q["questionStem"])

    return answer_questions


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Image Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_image(stem: Optional[str]) -> Optional[bool]:
    """Return True if the question stem references a clinical image, else None."""
    if not stem:
        return None
    return True if IMAGE_PATTERN.search(stem) else None


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3.5: Validation
# ═══════════════════════════════════════════════════════════════════════════════

def validate_question(q: dict) -> list[dict]:
    """Run lightweight heuristic checks on one question. Returns issue dicts."""
    issues = []
    qid = q.get("id", "unknown")

    # ── Error-level ──

    if q.get("correctAnswer") and q.get("choices"):
        if q["correctAnswer"] not in q["choices"]:
            issues.append({
                "id": qid, "severity": "error",
                "issue": (
                    f"correctAnswer '{q['correctAnswer']}' not in choices "
                    f"({', '.join(sorted(q['choices'].keys()))})"
                ),
            })

    if q.get("choices"):
        vals = list(q["choices"].values())
        if len(vals) != len(set(vals)):
            issues.append({
                "id": qid, "severity": "error",
                "issue": "Duplicate choice text detected",
            })

    # ── Warning-level ──

    for field in ("correctExplanation", "incorrectExplanation", "questionStem"):
        text = q.get(field)
        if not text:
            continue

        s = text.rstrip()
        if s and s[-1] not in '.?!)\'"':
            issues.append({
                "id": qid, "severity": "warning",
                "issue": f"{field} may be truncated (ends with: '...{s[-40:]}')",
            })

        if TRUNCATION_ENDING.search(text):
            issues.append({
                "id": qid, "severity": "warning",
                "issue": f"{field} appears truncated (ends mid-sentence)",
            })

        if text.count('(') > text.count(')'):
            issues.append({
                "id": qid, "severity": "warning",
                "issue": f"{field} has unbalanced parentheses (possible truncation)",
            })

    if q.get("correctExplanation") and len(q["correctExplanation"]) < 80:
        issues.append({
            "id": qid, "severity": "warning",
            "issue": f"correctExplanation suspiciously short ({len(q['correctExplanation'])} chars)",
        })

    if q.get("incorrectExplanation") and len(q["incorrectExplanation"]) < 50:
        issues.append({
            "id": qid, "severity": "warning",
            "issue": f"incorrectExplanation suspiciously short ({len(q['incorrectExplanation'])} chars)",
        })

    # ── Info-level ──

    if q.get("choices"):
        n = len(q["choices"])
        if n < 3:
            issues.append({"id": qid, "severity": "info", "issue": f"Only {n} choices"})
        elif n > 10:
            issues.append({"id": qid, "severity": "info", "issue": f"{n} choices (unusual)"})

    missing = [
        f for f in ("questionStem", "choices", "correctAnswer",
                     "correctExplanation", "incorrectExplanation", "system")
        if not q.get(f)
    ]
    if missing:
        sev = "warning" if "correctAnswer" in missing else "info"
        issues.append({"id": qid, "severity": sev, "issue": f"Missing: {', '.join(missing)}"})

    return issues


def find_question_gaps(questions: list[dict], expected: Optional[int] = None) -> Optional[dict]:
    """Check for missing question numbers in a parsed set."""
    if not questions:
        return None
    found = sorted(q["questionNumber"] for q in questions)
    hi = expected or max(found)
    missing = sorted(set(range(1, hi + 1)) - set(found))
    if missing:
        return {"expected": hi, "found": len(found), "missing": missing}
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="Parse CMS PDFs → structured JSON")
    ap.add_argument("--cms-dir", default="CMS", help="CMS source directory")
    ap.add_argument("--output-dir", default="Parsed", help="Output directory")
    ap.add_argument("--existing-output", default="output",
                    help="Previous run directory (for image-only PDFs)")
    ap.add_argument("--vision", action="store_true",
                    help="Enable GPT-4o Vision for image-only PDFs without existing output")
    ap.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"),
                    help="OpenAI API key (or OPENAI_API_KEY env var)")
    ap.add_argument("--test", action="store_true",
                    help="Process only the first PDF of each type")
    ap.add_argument("--dry-run", action="store_true",
                    help="Discover & classify only — don't parse")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    cms_dir = root / args.cms_dir
    output_dir = root / args.output_dir
    existing_dir = root / args.existing_output

    output_dir.mkdir(parents=True, exist_ok=True)

    # Vision AI client (lazy)
    vision_client = None
    if args.vision and OPENAI_AVAILABLE and args.api_key:
        vision_client = OpenAI(api_key=args.api_key)

    # ── Phase 1: Discover ────────────────────────────────────────────────────
    print("Phase 1: Discovering & classifying PDFs...\n")
    entries = discover_pdfs(cms_dir)

    counts = defaultdict(int)
    for e in entries:
        counts[e["type"]] += 1

    print(f"  Found {len(entries)} PDF sets:")
    for t in (OFFICIAL_TEXT, OFFICIAL_IMAGE, COMMUNITY, Q_ONLY):
        print(f"    {t:18s}  {counts.get(t, 0)}")
    print()

    if args.dry_run:
        for e in entries:
            print(f"  [{e['type']:18s}] {e['section']}/{e['number']}")
        return

    # ── Phase 2–6: Parse → Validate → Output ────────────────────────────────
    all_questions: list[dict] = []
    report: dict = {
        "runTimestamp": datetime.now().isoformat(),
        "summary": {},
        "byCategory": {},
        "skippedPdfs": [],
        "partialPdfs": [],
        "missingFields": [],
        "validationIssues": [],
        "questionGaps": [],
        "errors": [],
    }

    cat_stats = defaultdict(lambda: {"parsed": 0, "questions": 0, "complete": 0})
    tested_types: set[str] = set()

    for entry in entries:
        section = entry["section"]
        num = entry["number"]
        pdf_type = entry["type"]
        a_pdf = entry["a_pdf"]
        label = f"{section}/{num}"

        if args.test and pdf_type in tested_types:
            continue

        # Q-only → skip
        if pdf_type == Q_ONLY:
            print(f"  [SKIP     ] {label} (Q-only, no answer key)")
            report["skippedPdfs"].append({
                "pdf": f"{section}/{num} Q.pdf", "reason": "Q-only, no answer key",
            })
            continue

        print(f"  [{pdf_type:18s}] {label}...", end=" ", flush=True)
        questions: list[dict] = []

        try:
            if pdf_type == OFFICIAL_TEXT:
                questions = parse_official_text(a_pdf, section, num)

            elif pdf_type == COMMUNITY:
                questions = parse_community_pdf(a_pdf, section, num)
                q_pdf = entry.get("q_pdf")

                if q_pdf and vision_client:
                    q_data = parse_q_pdf_with_vision(q_pdf, vision_client)
                    if q_data:
                        questions = merge_community_with_q_data(questions, q_data)
                        filled = sum(1 for q in questions if q.get("questionStem"))
                        print(f"(merged {filled} stems from Q PDF)", end=" ")
                elif q_pdf:
                    report["partialPdfs"].append({
                        "pdf": f"{section}/{num}A.pdf",
                        "reason": "Community answer key; Q PDF exists but --vision not enabled",
                        "questionsFound": len(questions),
                    })
                else:
                    report["partialPdfs"].append({
                        "pdf": f"{section}/{num}A.pdf",
                        "reason": "Community answer key (no Q PDF found)",
                        "questionsFound": len(questions),
                    })

            elif pdf_type == OFFICIAL_IMAGE:
                existing = import_existing_output(existing_dir, section, num)
                if existing:
                    questions = [
                        normalize_imported_question(q, section, num) for q in existing
                    ]
                    print(f"(imported {len(questions)} from previous run)", end=" ")
                elif vision_client:
                    questions = parse_with_vision(a_pdf, section, num, vision_client)
                else:
                    report["errors"].append({
                        "pdf": f"{section}/{num}A.pdf",
                        "error": "Image-only PDF; no existing output and --vision not enabled",
                    })
                    print("→ NEEDS VISION AI")
                    continue

        except Exception as exc:
            report["errors"].append({
                "pdf": f"{section}/{num}A.pdf", "error": str(exc),
            })
            print(f"→ ERROR: {exc}")
            continue

        # Validate every question
        for q in questions:
            issues = validate_question(q)
            report["validationIssues"].extend(issues)

            missing = [
                f for f in ("questionStem", "choices", "correctAnswer",
                             "correctExplanation", "incorrectExplanation", "system")
                if not q.get(f)
            ]
            if missing:
                report["missingFields"].append({"id": q["id"], "missing": missing})

        # Gap check
        gaps = find_question_gaps(questions)
        if gaps:
            report["questionGaps"].append({"pdf": f"{section}/{num}A.pdf", **gaps})

        # Write per-PDF JSON
        slug = SECTION_SLUGS.get(section, section.lower().replace(" ", "_"))
        sec_dir = output_dir / slug
        sec_dir.mkdir(parents=True, exist_ok=True)

        out_path = sec_dir / f"cms_{num}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)

        complete = sum(
            1 for q in questions
            if all(q.get(k) for k in ("questionStem", "choices", "correctAnswer",
                                       "correctExplanation"))
        )
        print(f"→ {len(questions)} questions ({complete} complete) → {slug}/cms_{num}.json")

        all_questions.extend(questions)
        cat_stats[section]["parsed"] += 1
        cat_stats[section]["questions"] += len(questions)
        cat_stats[section]["complete"] += complete
        tested_types.add(pdf_type)

    # ── Combined output ──────────────────────────────────────────────────────
    with open(output_dir / "all_questions.json", 'w', encoding='utf-8') as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)

    # ── Report ───────────────────────────────────────────────────────────────
    total_q = len(all_questions)
    total_complete = sum(
        1 for q in all_questions
        if all(q.get(k) for k in ("questionStem", "choices", "correctAnswer",
                                   "correctExplanation"))
    )
    report["summary"] = {
        "totalPdfsFound": len(entries),
        "totalPdfsParsed": sum(s["parsed"] for s in cat_stats.values()),
        "totalPdfsSkipped": len(report["skippedPdfs"]),
        "totalQuestions": total_q,
        "totalComplete": total_complete,
        "totalPartial": total_q - total_complete,
        "totalWithImages": sum(1 for q in all_questions if q.get("image")),
        "validationErrors": sum(
            1 for i in report["validationIssues"] if i["severity"] == "error"
        ),
        "validationWarnings": sum(
            1 for i in report["validationIssues"] if i["severity"] == "warning"
        ),
    }
    report["byCategory"] = {k: dict(v) for k, v in cat_stats.items()}

    with open(output_dir / "parse_report.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # ── Summary ──────────────────────────────────────────────────────────────
    s = report["summary"]
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  PDFs found:            {s['totalPdfsFound']}")
    print(f"  PDFs parsed:           {s['totalPdfsParsed']}")
    print(f"  PDFs skipped:          {s['totalPdfsSkipped']}")
    print(f"  Total questions:       {s['totalQuestions']}")
    print(f"  Fully complete:        {s['totalComplete']}")
    print(f"  Partial / missing:     {s['totalPartial']}")
    print(f"  With images detected:  {s['totalWithImages']}")
    print(f"  Validation errors:     {s['validationErrors']}")
    print(f"  Validation warnings:   {s['validationWarnings']}")
    print(f"  Question gaps:         {len(report['questionGaps'])}")
    print(f"\n  Output → {output_dir}/")
    print(f"  Report → {output_dir}/parse_report.json")


if __name__ == "__main__":
    main()
