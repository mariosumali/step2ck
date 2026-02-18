#!/usr/bin/env python3
"""
Targeted repair script for known parsing issues.

Phase 1: Fix IM-6 explanations (re-parse from PDF text, no API needed)
Phase 2: Fix forms 7/8 missing choices (text-only GPT, cheap)
Phase 3: Process FM-5, EM-3, and fix Surgery 1 / Neurology 1 merge (Vision API)
"""

import json
import os
import re
import sys
import time
import random
import base64
import io
import argparse
from pathlib import Path
from typing import Optional

import pypdf

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


ROOT = Path(__file__).resolve().parent.parent
PARSED = ROOT / "Parsed"
CMS = ROOT / "CMS"

SECTION_CODES = {
    "1 Internal Medicine": "IM",
    "2 Surgery": "SURG",
    "3 OBGYN": "OB",
    "4 Pediatrics": "PEDS",
    "5 Neurology": "NEURO",
    "6 Psychiatry": "PSYCH",
    "7 Family Medicine": "FM",
    "8 Emergency Medicine": "EM",
}


# ─── Utility ─────────────────────────────────────────────────────────────────

def clean_text(s: str) -> str:
    s = re.sub(r'https?://\S+', '', s)
    s = re.sub(r'Exam Section\s*:.*?(?:\n|$)', '', s)
    s = re.sub(r'National Board.*?(?:\n|$)', '', s)
    s = re.sub(r'Next Score Report.*', '', s, flags=re.DOTALL)
    s = re.sub(r'■\s*Mark.*', '', s)
    s = re.sub(r'^\s*~\s*', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"    Saved {path.name} ({len(data)} questions)")


def vision_call(client, prompt: str, image_b64: str, label: str,
                max_retries: int = 5) -> Optional[dict]:
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
                print(f"      Rate limited ({label}), waiting {wait:.1f}s...")
                time.sleep(wait)
            else:
                print(f"      Vision error ({label}): {e}")
                return None
    return None


def text_api_call(client, prompt: str, label: str,
                  model: str = "gpt-4o-mini", max_retries: int = 5) -> Optional[str]:
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str:
                wait = (2 ** attempt) + random.random()
                print(f"      Rate limited ({label}), waiting {wait:.1f}s...")
                time.sleep(wait)
            else:
                print(f"      Text API error ({label}): {e}")
                return None
    return None


def pdf_page_to_b64(pdf_path: Path, page_idx: int) -> str:
    doc = fitz.open(str(pdf_path))
    pix = doc[page_idx].get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    doc.close()
    return base64.b64encode(img_bytes).decode()


# ─── Phase 1: Fix IM-6 and similar explanations ─────────────────────────────

def reparse_explanations_for_pdf(pdf_path: Path, json_path: Path):
    """Re-extract explanations from a text-extractable PDF for questions missing them."""
    questions = load_json(json_path)

    reader = pypdf.PdfReader(str(pdf_path))
    full_text = "\n".join(p.extract_text() or "" for p in reader.pages)

    chunks = re.split(r'(?=Exam Section\s*:\s*Item\s+\d+\s+of\s+\d+)', full_text)

    chunk_map: dict[int, str] = {}
    for ch in chunks:
        m = re.search(r'Item\s+(\d+)\s+of', ch)
        if m:
            chunk_map[int(m.group(1))] = ch

    fixed = 0
    for q in questions:
        qn = q["questionNumber"]
        ca = q.get("correctAnswer")

        needs_answer = not ca
        needs_expl = not q.get("correctExplanation")

        if not needs_answer and not needs_expl:
            continue

        ch = chunk_map.get(qn)
        if not ch:
            continue

        # Find where choices end
        last_choice_end = None
        for cm in re.finditer(r'\n\s*[A-L]\s*[)}\}]\s*[^\n]+', ch):
            last_choice_end = cm.end()
        if not last_choice_end:
            continue

        after_choices = ch[last_choice_end:]

        # Try to find correct answer if missing
        if needs_answer:
            m = re.search(r'\(([A-L])\s+is\s+correct\)', after_choices, re.IGNORECASE)
            if m:
                ca = m.group(1).upper()
                q["correctAnswer"] = ca

            if not ca:
                m = re.search(r'\(([A-L])\)\s+\w', after_choices)
                if m:
                    ca = m.group(1).upper()
                    q["correctAnswer"] = ca

        if not needs_expl or not ca:
            continue

        correct_expl = None
        incorrect_expl = None

        # Format A: "(X is correct) ... (Y is incorrect) ..."
        is_correct_m = re.search(
            rf'\({ca}\s+is\s+correct\)', after_choices, re.IGNORECASE
        )
        if is_correct_m:
            # Everything up to "(X is correct)" inclusive is the correct explanation preamble
            # Then look for first "(Y is incorrect)" to split
            text_after_correct = after_choices[is_correct_m.end():]
            incorrect_m = re.search(
                r'\([A-L](?:,\s*[A-L])*\s+(?:is|are)\s+incorrect\)',
                text_after_correct, re.IGNORECASE,
            )
            full_correct = after_choices[:is_correct_m.end()]
            if incorrect_m:
                full_correct += text_after_correct[:incorrect_m.start()]
                incorrect_expl = clean_text(text_after_correct[incorrect_m.start():])
            correct_expl = clean_text(full_correct)

        # Format B: "(D) Explanation text ... (A, B) other explanation ..."
        if not correct_expl:
            paren_m = re.search(rf'\({ca}\)\s+\w', after_choices)
            if paren_m:
                block = after_choices[paren_m.start():]
                # Split at next "(OTHER_LETTER)" that's not the correct answer
                other_m = re.search(
                    r'\([A-L](?:,\s*[A-L])*\)\s',
                    block[len(paren_m.group(0)):],
                )
                if other_m:
                    split_pos = len(paren_m.group(0)) + other_m.start()
                    correct_expl = clean_text(block[:split_pos])
                    incorrect_expl = clean_text(block[split_pos:])
                else:
                    correct_expl = clean_text(block)

        # Format C: free text explanation (no parenthetical markers)
        if not correct_expl:
            raw = clean_text(after_choices)
            if raw and len(raw) > 40:
                correct_expl = raw

        if correct_expl:
            q["correctExplanation"] = correct_expl
            if incorrect_expl:
                q["incorrectExplanation"] = incorrect_expl
            fixed += 1

    if fixed:
        save_json(questions, json_path)
    return fixed


# ─── Phase 2: Fix forms 7/8 missing choices ─────────────────────────────────

def fix_missing_choices(client) -> int:
    """Use text-only GPT to reconstruct missing choice text from explanations."""

    files_to_fix = []
    for cat_dir in sorted(os.listdir(PARSED)):
        cat_path = PARSED / cat_dir
        if not cat_path.is_dir():
            continue
        for fname in sorted(os.listdir(cat_path)):
            if not fname.endswith(".json") or not fname.startswith("cms_"):
                continue
            fpath = cat_path / fname
            questions = load_json(fpath)

            broken = [
                q for q in questions
                if q.get("correctAnswer") and q.get("choices")
                and q["correctAnswer"] not in q["choices"]
            ]
            if broken:
                files_to_fix.append((fpath, questions, broken))

    total_fixed = 0

    for fpath, questions, broken in files_to_fix:
        print(f"  {fpath.relative_to(PARSED)}: {len(broken)} missing choices")
        file_fixed = 0

        for q in broken:
            ca = q["correctAnswer"]
            choices = q["choices"]
            expl = q.get("correctExplanation", "") or ""
            stem = q.get("questionStem", "") or ""

            existing_choices_str = "\n".join(
                f"{k}) {v}" for k, v in sorted(choices.items())
            )

            prompt = (
                f"This USMLE Step 2 CK question has correct answer {ca}, but the text "
                f"for choice {ca} is missing. Based on the context below, what would "
                f"choice {ca} say? Reply with ONLY the choice text, nothing else.\n\n"
                f"Question: {stem[:300]}\n\n"
                f"Existing choices:\n{existing_choices_str}\n\n"
                f"Explanation: {expl[:500]}"
            )

            result = text_api_call(
                client, prompt, f"Q{q.get('questionNumber', '?')} choice {ca}"
            )

            if result:
                result = result.strip().strip('"').strip("'")
                result = re.sub(rf'^{ca}\s*[).:]\s*', '', result)
                if result and len(result) > 1:
                    q["choices"][ca] = result
                    file_fixed += 1

        if file_fixed:
            save_json(questions, fpath)
            total_fixed += file_fixed
            print(f"    Fixed {file_fixed} choices")

    return total_fixed


# ─── Phase 3: Vision AI for missing files and merge fixes ───────────────────

FULL_VISION_PROMPT = (
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
    'IMPORTANT: Include ALL answer choices in the "choices" object, including the '
    'correct answer. Every choice letter visible in the image must be present.\n\n'
    'If this page is NOT a question (title page, TOC, etc.), return: {"skip": true}\n'
    'Return ONLY valid JSON, no markdown fences.'
)

Q_ONLY_VISION_PROMPT = (
    "Extract the USMLE question from this image. This page contains ONLY the "
    "question — no answer or explanation. Return a JSON object:\n"
    '{\n'
    '  "questionNumber": <int>,\n'
    '  "questionStem": "<full question text>",\n'
    '  "choices": {"A": "...", "B": "...", ...},\n'
    '  "hasImage": <true if the page contains a clinical image/photo/x-ray, else false>\n'
    '}\n\n'
    'IMPORTANT: Include ALL answer choices in the "choices" object.\n'
    'If this page is NOT a question (blank, title page, etc.), return: {"skip": true}\n'
    'Return ONLY valid JSON, no markdown fences.'
)


def process_image_pdf(pdf_path: Path, section_name: str, cms_number: str,
                      client, prompt: str = FULL_VISION_PROMPT) -> list[dict]:
    """Extract questions from an image-only PDF via Vision AI."""
    section_code = SECTION_CODES.get(section_name, "UNK")
    doc = fitz.open(str(pdf_path))
    page_count = len(doc)
    doc.close()

    print(f"    Processing {page_count} pages via Vision AI...")
    questions = []

    for i in range(page_count):
        img_b64 = pdf_page_to_b64(pdf_path, i)
        data = vision_call(client, prompt, img_b64, f"p{i+1}")

        if data and not data.get("skip"):
            q_num = data.get("questionNumber", i + 1)
            questions.append({
                "questionNumber": q_num,
                "questionStem": data.get("questionStem"),
                "choices": data.get("choices"),
                "correctAnswer": data.get("correctAnswer"),
                "correctExplanation": data.get("correctExplanation"),
                "incorrectExplanation": data.get("incorrectExplanation"),
                "image": True if data.get("hasImage") else None,
                "id": f"{section_code}-{cms_number}-{q_num}",
                "section": section_code,
                "subsection": f"CMS-{cms_number}",
                "system": None,
            })

        if (i + 1) % 10 == 0:
            print(f"      Progress: {i+1}/{page_count}")

    questions.sort(key=lambda q: q.get("questionNumber", 0))
    return questions


def fix_community_merge(q_pdf: Path, json_path: Path, section_name: str,
                        cms_number: str, client) -> int:
    """Re-run Vision AI on a community Q PDF and merge by POSITION."""
    section_code = SECTION_CODES.get(section_name, "UNK")
    questions = load_json(json_path)

    doc = fitz.open(str(q_pdf))
    page_count = len(doc)
    doc.close()

    print(f"    Extracting stems from Q PDF ({page_count} pages)...")
    q_stems = []

    for i in range(page_count):
        img_b64 = pdf_page_to_b64(q_pdf, i)
        data = vision_call(client, Q_ONLY_VISION_PROMPT, img_b64, f"Q-p{i+1}")

        if data and not data.get("skip"):
            q_stems.append({
                "questionNumber": data.get("questionNumber", i + 1),
                "questionStem": data.get("questionStem"),
                "choices": data.get("choices"),
                "hasImage": data.get("hasImage", False),
            })

        if (i + 1) % 10 == 0:
            print(f"      Progress: {i+1}/{page_count}")

    print(f"      Got {len(q_stems)} stems from Q PDF")

    # Merge by POSITION: 1st Q-PDF stem → 1st A-PDF answer, etc.
    filled = 0
    for idx, q in enumerate(questions):
        if idx < len(q_stems):
            src = q_stems[idx]
            if not q.get("questionStem") and src.get("questionStem"):
                q["questionStem"] = src["questionStem"]
            if not q.get("choices") and src.get("choices"):
                q["choices"] = src["choices"]
            if src.get("hasImage"):
                q["image"] = True
            if q.get("questionStem") and q.get("choices"):
                filled += 1

    save_json(questions, json_path)
    return filled


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Repair known parsing issues")
    ap.add_argument("--phase", type=int, choices=[1, 2, 3],
                    help="Run only a specific phase (1=explanations, 2=choices, 3=vision)")
    ap.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    args = ap.parse_args()

    client = None
    if OPENAI_AVAILABLE and args.api_key:
        client = OpenAI(api_key=args.api_key)

    run_all = args.phase is None

    # ═══ Phase 1: Fix explanations from text-extractable PDFs ═══════════════
    if run_all or args.phase == 1:
        print("\n" + "=" * 60)
        print("PHASE 1: Fix missing explanations (no API needed)")
        print("=" * 60)

        targets = [
            (CMS / "1 Internal Medicine" / "6A.pdf",
             PARSED / "1_internal_medicine" / "cms_6.json"),
        ]

        # Also scan for other text-extractable PDFs with many missing explanations
        text_pdf_map = {
            "1_internal_medicine": "1 Internal Medicine",
            "2_surgery": "2 Surgery",
            "3_obgyn": "3 OBGYN",
            "4_pediatrics": "4 Pediatrics",
            "5_neurology": "5 Neurology",
            "6_psychiatry": "6 Psychiatry",
            "7_family_medicine": "7 Family Medicine",
            "8_emergency_medicine": "8 Emergency Medicine",
        }

        for cat_slug, cat_name in text_pdf_map.items():
            cat_dir = PARSED / cat_slug
            if not cat_dir.is_dir():
                continue
            for fname in sorted(os.listdir(cat_dir)):
                if not fname.endswith(".json") or not fname.startswith("cms_"):
                    continue
                num = fname.replace("cms_", "").replace(".json", "")
                pdf_path = CMS / cat_name / f"{num}A.pdf"
                json_path = cat_dir / fname

                # Skip if already in targets
                if any(j == json_path for _, j in targets):
                    continue

                if not pdf_path.exists():
                    continue

                # Check if PDF is text-extractable
                try:
                    reader = pypdf.PdfReader(str(pdf_path))
                    test_text = (reader.pages[0].extract_text() or "").replace(
                        "http://www.usmle.org", ""
                    ).replace("https://t.me/USMLENBME2CK", "").strip()
                    if len(test_text) < 50:
                        continue
                except Exception:
                    continue

                # Check if this file has missing explanations
                questions = load_json(json_path)
                missing_expl = sum(
                    1 for q in questions
                    if q.get("correctAnswer") and not q.get("correctExplanation")
                )
                if missing_expl >= 3:
                    targets.append((pdf_path, json_path))

        total_fixed = 0
        for pdf_path, json_path in targets:
            name = json_path.relative_to(PARSED)
            print(f"\n  Reparsing explanations: {name}")
            fixed = reparse_explanations_for_pdf(pdf_path, json_path)
            total_fixed += fixed
            print(f"    Fixed {fixed} explanations")

        print(f"\n  Phase 1 total: {total_fixed} explanations fixed")

    # ═══ Phase 2: Fix missing choices via text API ══════════════════════════
    if run_all or args.phase == 2:
        print("\n" + "=" * 60)
        print("PHASE 2: Fix missing choices (text API)")
        print("=" * 60)

        if not client:
            print("  SKIPPED — no API key available")
        else:
            total_fixed = fix_missing_choices(client)
            print(f"\n  Phase 2 total: {total_fixed} choices fixed")

    # ═══ Phase 3: Vision AI for missing files + merge fixes ═════════════════
    if run_all or args.phase == 3:
        print("\n" + "=" * 60)
        print("PHASE 3: Vision AI (missing files + merge fixes)")
        print("=" * 60)

        if not client:
            print("  SKIPPED — no API key available")
        elif not FITZ_AVAILABLE:
            print("  SKIPPED — pymupdf not available")
        else:
            # 3a: Process FM-5 and EM-3
            missing_files = [
                ("7 Family Medicine", "5", "FM", "7_family_medicine"),
                ("8 Emergency Medicine", "3", "EM", "8_emergency_medicine"),
            ]

            for section_name, num, code, slug in missing_files:
                pdf_path = CMS / section_name / f"{num}A.pdf"
                json_path = PARSED / slug / f"cms_{num}.json"

                if json_path.exists():
                    existing = load_json(json_path)
                    complete = sum(
                        1 for q in existing
                        if all(q.get(k) for k in
                               ("questionStem", "choices", "correctAnswer",
                                "correctExplanation"))
                    )
                    if complete > 5:
                        print(f"\n  {slug}/cms_{num}.json already has {complete}"
                              f" complete questions, skipping")
                        continue

                if not pdf_path.exists():
                    print(f"\n  {pdf_path} not found, skipping")
                    continue

                print(f"\n  Processing {section_name}/{num}A.pdf (full Vision AI)...")
                questions = process_image_pdf(
                    pdf_path, section_name, num, client
                )
                if questions:
                    save_json(questions, json_path)
                    complete = sum(
                        1 for q in questions
                        if all(q.get(k) for k in
                               ("questionStem", "choices", "correctAnswer",
                                "correctExplanation"))
                    )
                    print(f"    → {len(questions)} questions ({complete} complete)")

            # 3b: Fix community merge alignment (Surgery 1, Neurology 1)
            merge_fixes = [
                ("2 Surgery", "1", "2_surgery"),
                ("5 Neurology", "1", "5_neurology"),
            ]

            for section_name, num, slug in merge_fixes:
                q_pdf = CMS / section_name / f"{num} Q.pdf"
                json_path = PARSED / slug / f"cms_{num}.json"

                if not q_pdf.exists() or not json_path.exists():
                    print(f"\n  Missing files for {section_name}/{num}, skipping")
                    continue

                # Check how many are missing stems
                questions = load_json(json_path)
                missing_stems = sum(1 for q in questions if not q.get("questionStem"))

                if missing_stems < 5:
                    print(f"\n  {slug}/cms_{num}.json: only {missing_stems} "
                          f"missing stems, skipping")
                    continue

                print(f"\n  Fixing merge: {section_name}/{num} "
                      f"({missing_stems} missing stems)...")
                filled = fix_community_merge(
                    q_pdf, json_path, section_name, num, client
                )
                print(f"    → Merged {filled} stems by position")

    # ═══ Final summary ══════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("REPAIR SUMMARY")
    print("=" * 60)

    total = 0
    complete = 0
    for root, dirs, files in os.walk(PARSED):
        for f in files:
            if f.startswith("cms_") and f.endswith(".json"):
                qs = load_json(Path(root) / f)
                total += len(qs)
                complete += sum(
                    1 for q in qs
                    if all(q.get(k) for k in
                           ("questionStem", "choices", "correctAnswer",
                            "correctExplanation"))
                )

    answer_not_in_choices = 0
    for root, dirs, files in os.walk(PARSED):
        for f in files:
            if f.startswith("cms_") and f.endswith(".json"):
                qs = load_json(Path(root) / f)
                answer_not_in_choices += sum(
                    1 for q in qs
                    if q.get("correctAnswer") and q.get("choices")
                    and q["correctAnswer"] not in q["choices"]
                )

    print(f"  Total questions:        {total}")
    print(f"  Fully complete:         {complete}")
    print(f"  Answer not in choices:  {answer_not_in_choices}")
    print(f"  Completion rate:        {complete/total*100:.1f}%")


if __name__ == "__main__":
    main()
