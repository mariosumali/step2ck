#!/usr/bin/env python3
"""
USMLE Step 2 CK PDF to JSON Parser - GPT-4 Vision Version

Uses GPT-4 Vision for accurate extraction of questions from PDF images.
Runs in parallel for faster processing.
"""

import json
import os
import re
import base64
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import pypdf
from pdf2image import convert_from_path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = None

# Section mappings
SECTION_MAPPINGS = {
    "1 Internal Medicine": "Internal Medicine",
    "2 Surgery": "Surgery",
    "3 OBGYN": "OBGYN",
    "4 Pediatrics": "Pediatrics",
    "5 Neurology": "Neurology",
    "6 Psychiatry": "Psychiatry",
    "7 Family Medicine": "Family Medicine",
    "8 Emergency Medicine": "Emergency Medicine",
}

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

# PDFs to skip (answer keys, not actual question banks)
SKIP_PDFS = {"1A.pdf", "2A.pdf"}


def encode_image_to_base64(image) -> str:
    """Convert PIL Image to base64 string."""
    import io
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def extract_question_from_image(image, question_num: int, section_code: str, cms_num: str) -> Optional[dict]:
    """Use GPT-4 Vision to extract question data from a page image."""
    global client
    
    base64_image = encode_image_to_base64(image)
    
    prompt = """Extract the USMLE question from this image. Return a JSON object with exactly these fields:
{
    "questionNumber": <number>,
    "questionStem": "<the full question text>",
    "choices": {"A": "<choice A text>", "B": "<choice B text>", ...},
    "correctAnswer": "<letter A-L>",
    "correctExplanation": "<explanation for correct answer>",
    "incorrectExplanation": "<explanation for incorrect answers if present>"
}

If this page doesn't contain a complete question (e.g., it's a title page or table of contents), return: {"skip": true}

Important:
- Extract ALL choice options (A through E, or more if present)
- The correctAnswer should be just the letter
- Include the full explanation text
- Return ONLY valid JSON, no markdown formatting"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4o for vision
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up markdown formatting if present
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n?', '', result_text)
            result_text = re.sub(r'\n?```$', '', result_text)
        
        data = json.loads(result_text)
        
        if data.get("skip"):
            return None
        
        # Add metadata
        data["id"] = f"{section_code}-{cms_num}-{data.get('questionNumber', question_num)}"
        data["section"] = SECTION_MAPPINGS.get(section_code, section_code)
        data["subsection"] = f"CMS-{cms_num}"
        
        return data
        
    except Exception as e:
        print(f"    Error extracting Q{question_num}: {e}")
        return None


def process_pdf_with_gpt(pdf_path: str, section_name: str, force_gpt: bool = False, max_workers: int = 5) -> tuple[list[dict], list[str]]:
    """Process a single PDF using GPT-4 Vision with parallel page processing."""
    global client
    
    questions = []
    issues = []
    
    # Extract CMS number from filename (e.g., "3A.pdf" -> "3")
    filename = os.path.basename(pdf_path)
    cms_match = re.match(r'(\d+)A\.pdf', filename)
    if not cms_match:
        return [], [f"Invalid filename format: {filename}"]
    
    cms_num = cms_match.group(1)
    section_code = SECTION_CODES.get(section_name, "UNK")
    
    print(f"\nProcessing: {section_name}/{filename}")
    
    # First try regular text extraction
    reader = pypdf.PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages[:3]:
        text = page.extract_text()
        if text:
            full_text += text
    
    # Check if it has meaningful content (not just watermarks)
    has_questions = (
        "Exam Section" in full_text and 
        ("Correct Answer" in full_text or re.search(r'\([A-E]\)\s*\w', full_text))
    )
    
    if has_questions and not force_gpt:
        # Use regular text extraction (faster, works for text-based PDFs)
        print(f"  Using text extraction...")
        from pdf_parser import parse_questions, extract_pdf_text
        text = extract_pdf_text(pdf_path, use_ocr_fallback=False)
        questions = parse_questions(text, section_name, cms_num)
        return questions, []
    
    # Use GPT-4 Vision for image-based PDFs
    print(f"  Using GPT-4 Vision (image-based PDF)...")
    
    # Convert PDF pages to images
    try:
        images = convert_from_path(pdf_path, dpi=150)  # Lower DPI for faster processing
        print(f"    {len(images)} pages to process")
    except Exception as e:
        return [], [f"PDF conversion error: {e}"]
    
    # Process pages in parallel
    def process_page(args):
        idx, image = args
        return extract_question_from_image(image, idx + 1, section_code, cms_num)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_page, (i, img)): i for i, img in enumerate(images)}
        
        for future in as_completed(futures):
            result = future.result()
            if result and not result.get("skip"):
                questions.append(result)
    
    # Sort by question number
    questions.sort(key=lambda q: q.get("questionNumber", 0))
    
    print(f"    Extracted {len(questions)} questions")
    
    return questions, issues


def main():
    global client
    
    import argparse
    parser = argparse.ArgumentParser(description="Extract USMLE questions from PDFs using GPT-4 Vision")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"), help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--cms-dir", default="CMS", help="Directory containing CMS PDFs")
    parser.add_argument("--output-dir", default="output", help="Output directory for JSON files")
    parser.add_argument("--parallel", type=int, default=3, help="Number of parallel API calls per PDF")
    parser.add_argument("--test", action="store_true", help="Process only one PDF for testing")
    parser.add_argument("--force-gpt", action="store_true", help="Force usage of GPT-4 Vision even for text-based PDFs")
    parser.add_argument("--start-from", help="Resume processing from a specific section/file (e.g. '1 Internal Medicine/3A.pdf')")
    args = parser.parse_args()
    
    if not args.api_key:
        print("Error: OPENAI_API_KEY not set. Use --api-key or set the environment variable.")
        return
    
    # Initialize OpenAI client
    client = OpenAI(api_key=args.api_key)
    
    # Find all PDF files to process
    cms_path = Path(args.cms_dir)
    pdf_files = []
    
    for section_dir in sorted(cms_path.iterdir()):
        if not section_dir.is_dir():
            continue
        
        section_name = section_dir.name
        if section_name not in SECTION_MAPPINGS:
            continue
        
        for pdf_file in sorted(section_dir.glob("*A.pdf")):
            # Skip answer keys (1A.pdf, 2A.pdf)
            if pdf_file.name in SKIP_PDFS:
                print(f"Skipping {section_name}/{pdf_file.name} (answer key)")
                continue
            
            pdf_files.append((str(pdf_file), section_name))
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    if args.test:
        pdf_files = pdf_files[:1]
        print("Test mode: processing only first PDF")
    
    # Process PDFs
    all_questions = []
    output_path = Path(args.output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Group by section for output
    section_questions = {}
    
    start_found = False if args.start_from else True
    
    for pdf_path, section_name in pdf_files:
        # Check start_from logic
        if not start_found:
            current_identifier = f"{section_name}/{os.path.basename(pdf_path)}"
            if args.start_from in current_identifier:
                start_found = True
            else:
                continue
        
        # Determine output filename
        section_slug = section_name.lower().replace(" ", "_")
        section_dir = output_path / section_slug
        section_dir.mkdir(exist_ok=True)
        safe_name = f"questions_{os.path.basename(pdf_path)}.json"
        output_file = section_dir / safe_name
        
        # SKIP if already exists (Robust Resume)
        if output_file.exists() and not args.force_gpt: 
            # Note: --force-gpt also acts as force-overwrite if we want, 
            # but usually we want to skip done files. 
            # Let's say: if content exists, skip. 
            # To force re-process, user must delete files or we add --overwrite.
            # For now, let's assume we want to fill gaps.
            print(f"Skipping {pdf_path.name} (already exists)")
            continue

        questions, issues = process_pdf_with_gpt(pdf_path, section_name, force_gpt=args.force_gpt, max_workers=args.parallel)
        
        if questions:
            all_questions.extend(questions)
            with open(output_file, "w") as f:
                json.dump(questions, f, indent=2)
            print(f"  Saved {len(questions)} questions to {output_file.name}")

    # Merge all individual files into section-level all_questions.json
    print("\nMerging results...")
    for section_slug in [d.name for d in output_path.iterdir() if d.is_dir()]:
        section_dir = output_path / section_slug
        combined = []
        for json_file in section_dir.glob("questions_*.json"):
            try:
                with open(json_file) as f:
                    combined.extend(json.load(f))
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        # Sort by question number if possible? Or source?
        # combined.sort(key=lambda x: x.get('questionNumber', 0))
        
        if combined:
            with open(section_dir / "all_questions.json", "w") as f:
                json.dump(combined, f, indent=2)
            print(f"Merged {len(combined)} questions for {section_slug}")

    # Also merge everything into one GIANT all_questions.json for valid references
    final_combined = []
    for json_file in output_path.glob("**/questions_*.json"):
        try:
            with open(json_file) as f:
                final_combined.extend(json.load(f))
        except: pass
    
    with open(output_path / "all_questions.json", "w") as f:
        json.dump(final_combined, f, indent=2)
    print(f"Total extracted questions: {len(final_combined)}")
    
    combined_file = output_path / "all_questions.json"
    # Logic to merge with existing combined file if it exists?
    # For simplicity, just rewrite with what we have in this run, user can merge manually or rerun all.
    # But let's at least try to read existing main file if we're in resume mode
    
    final_questions = []
    if args.start_from and combined_file.exists():
         try:
            with open(combined_file) as f:
                final_questions = json.load(f)
         except: pass
    
    final_questions.extend(all_questions)
    
    with open(combined_file, "w") as f:
        json.dump(final_questions, f, indent=2)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total questions processed this run: {len(all_questions)}")
    print(f"Total questions in combined file: {len(final_questions)}")


if __name__ == "__main__":
    main()
