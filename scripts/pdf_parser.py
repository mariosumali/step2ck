#!/usr/bin/env python3
"""
USMLE Step 2 CK PDF to JSON Parser

This script extracts questions, answers, and explanations from NBME CMS PDF files
and converts them to structured JSON format. Supports both text-based and image-based
PDFs (using OCR for image-based).
"""

import json
import os
import re
from pathlib import Path
from typing import Optional
import pypdf

# Optional OCR imports - only used for image-based PDFs
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: OCR dependencies not available. Install with: pip install pdf2image pytesseract")


# Section name mappings
SECTION_MAPPINGS = {
    "1 Internal Medicine": "Internal Medicine",
    "2 Surgery": "Surgery",
    "3 OBGYN": "OBGYN",
    "4 Pediatrics": "Pediatrics",
    "5 Neurology": "Neurology",
    "6 Psychiatry": "Psychiatry",
    "7 Family Medicine": "Family Medicine",
    "8 Emergency Medicine": "Emergency Medicine",
    "Sample Items": "Sample Items"
}

# Short codes for IDs
SECTION_CODES = {
    "1 Internal Medicine": "IM",
    "2 Surgery": "SURG",
    "3 OBGYN": "OB",
    "4 Pediatrics": "PEDS",
    "5 Neurology": "NEURO",
    "6 Psychiatry": "PSYCH",
    "7 Family Medicine": "FM",
    "8 Emergency Medicine": "EM",
    "Sample Items": "SAMPLE"
}


def extract_pdf_text_ocr(pdf_path: str) -> str:
    """Extract text from PDF using OCR (for image-based PDFs)."""
    if not OCR_AVAILABLE:
        return ""
    
    print(f"  Using OCR for image-based PDF...")
    full_text = ""
    try:
        # Convert PDF to images (200 DPI is good balance of quality vs speed)
        images = convert_from_path(pdf_path, dpi=200)
        
        for i, image in enumerate(images):
            # Run OCR on each page
            page_text = pytesseract.image_to_string(image, lang='eng')
            full_text += page_text + "\n\n"
            
            # Progress indicator for large PDFs
            if (i + 1) % 20 == 0:
                print(f"    OCR progress: {i + 1}/{len(images)} pages...")
        
        print(f"    OCR complete: {len(images)} pages processed")
    except Exception as e:
        print(f"    OCR error: {e}")
        return ""
    
    return full_text


def extract_pdf_text(pdf_path: str, use_ocr_fallback: bool = True) -> str:
    """Extract all text from a PDF file, falling back to OCR if needed."""
    reader = pypdf.PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            full_text += page_text + "\n\n"
    
    # Check if we got meaningful content - not just watermarks
    # Look for indicators of actual question content
    has_meaningful_content = (
        "Exam Section" in full_text or
        "Item" in full_text and "of 50" in full_text or
        re.search(r'[A-E]\)\s+\w{5,}', full_text) is not None or  # Choice pattern
        "Correct Answer" in full_text
    )
    
    # If text extraction got only watermarks or minimal content, try OCR
    if use_ocr_fallback and not has_meaningful_content and OCR_AVAILABLE:
        return extract_pdf_text_ocr(pdf_path)
    
    return full_text


def parse_table_of_contents(text: str) -> dict[int, str]:
    """
    Parse the table of contents from page 1 to map question numbers to systems.
    Returns a dict mapping question number to system name.
    """
    system_mapping = {}
    
    # Pattern to match system lines like "System: Cardiovascular : 2,3,6,21,31,33,35,40,"
    toc_pattern = r'SY\.?stem:?\s*([^:]+):\s*([\d,\s]+)'
    
    matches = re.findall(toc_pattern, text, re.IGNORECASE)
    
    for system_name, numbers_str in matches:
        system_name = system_name.strip()
        # Clean up system name
        system_name = re.sub(r'\s+', ' ', system_name)
        
        # Parse question numbers
        numbers = re.findall(r'\d+', numbers_str)
        for num in numbers:
            system_mapping[int(num)] = system_name
    
    return system_mapping


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def parse_questions(text: str, section_name: str, cms_number: str) -> list[dict]:
    """
    Parse all questions from the PDF text.
    Returns a list of question dictionaries.
    """
    questions = []
    section_code = SECTION_CODES.get(section_name, "UNK")
    
    # Parse table of contents for system mapping
    system_mapping = parse_table_of_contents(text)
    
    # Split text into individual questions using "Exam Section : Item" as delimiter
    # Handle both "Exam Section :" and "Exam Section:" patterns
    question_splits = re.split(r'(?=Exam Section\s*:\s*Item\s+\d+\s+of\s+\d+)', text)
    
    for chunk in question_splits:
        if not chunk.strip():
            continue
            
        # Extract question number
        item_match = re.search(r'Item\s+(\d+)\s+of\s+(\d+)', chunk)
        if not item_match:
            continue
            
        question_num = int(item_match.group(1))
        total_questions = int(item_match.group(2))
        
        # Extract question stem - try multiple patterns
        # Pattern 1: After Self-Assessment with any markers
        stem_match = re.search(
            r"Self-Assessment\s*\n?[^\d]*?(\d+)\.\s*(.*?)(?=\n[A-L][)\}])",
            chunk,
            re.DOTALL
        )
        
        if not stem_match:
            # Pattern 2: Look for question number with various markers ('I, ~, X, etc.)
            stem_match = re.search(
                r"['\"\u2018\u2019~\u2713\u25A0XI]+\s*(\d+)\.\s*(.*?)(?=\n[A-L][)\}])",
                chunk,
                re.DOTALL
            )
        
        if not stem_match:
            # Pattern 3: Most flexible - just find "N. Text" pattern before choices
            stem_match = re.search(
                r"\n\s*(\d+)\.\s+([A-Z].*?)(?=\n[A-L][)\}])",
                chunk,
                re.DOTALL
            )
        
        if not stem_match:
            print(f"Warning: Could not extract stem for question {question_num}")
            continue
        
        question_stem = clean_text(stem_match.group(2))
        
        # Extract answer choices (A-L possible for extended questions)
        choices = {}
        
        # Process line by line to handle both single and two-column formats
        # Use [)\}] to match both ) and } as OCR sometimes confuses them
        lines = chunk.split('\n')
        for line in lines:
            # First check for two-column format: "A) text1 F) text2"
            two_col_match = re.match(r'([A-L])[)\}]\s*(.+?)\s+([A-L])[)\}]\s*(.+?)$', line.strip())
            if two_col_match:
                choices[two_col_match.group(1)] = clean_text(two_col_match.group(2))
                choices[two_col_match.group(3)] = clean_text(two_col_match.group(4))
            else:
                # Check for single-column format: "A) text" or "A} text"
                single_match = re.match(r'([A-L])[)\}]\s*(.+?)$', line.strip())
                if single_match:
                    letter = single_match.group(1)
                    text = single_match.group(2)
                    # Don't capture if this looks like it's from the explanation section
                    if 'Choice' not in text and letter not in choices:
                        choices[letter] = clean_text(text)
        
        if not choices:
            print(f"Warning: No choices found for question {question_num}")
            continue
        
        # Extract correct answer - handle multiple patterns
        # Pattern 1: "Correct Answer: E" or "Correct Answer : E" or "CorrectAnswer: E"
        correct_match = re.search(r'Correct\s*Answer\s*:\s*([A-L])\.?\s*', chunk, re.IGNORECASE)
        
        # Pattern 2: PAREN format - look for "(X) For/The/This/In" pattern in explanation
        # This format has "(X) Explanation..." where X is the correct answer
        if not correct_match:
            # Look for (X) followed by explanation-starting words
            paren_pattern = r'\(([A-L])\)\s*(For|The|This|In|A\s|An\s|If|When|Because|Since|As\s)'
            paren_match = re.search(paren_pattern, chunk)
            if paren_match:
                correct_match = paren_match
        
        # Pattern 3: "(X is correct)" or "(X) is correct" format
        if not correct_match:
            correct_pattern = r'\(([A-L])\s+is\s+correct\)|\(([A-L])\)\s+is\s+correct'
            correct_only_match = re.search(correct_pattern, chunk, re.IGNORECASE)
            if correct_only_match:
                # Get the letter from whichever group matched
                letter = correct_only_match.group(1) or correct_only_match.group(2)
                correct_match = type('obj', (object,), {'group': lambda self, n: letter.upper() if n == 1 else None})()
        
        if not correct_match:
            print(f"Warning: No correct answer found for question {question_num}")
            continue
        
        correct_answer = correct_match.group(1).upper()
        
        # If correct answer is not in choices, try to recover it
        # This happens when PDF text extraction corrupts the choice letter (e.g., "E)" becomes "tfil")
        if correct_answer not in choices:
            recovered = False
            
            # Pattern 1: Look for "LETTER text" without parenthesis before Correct Answer
            # e.g., "B Acute urethral obstruction" or "E Pulmonary edema"
            pattern1 = rf'\n\s*1?\s*\n?\s*{correct_answer}\s+([A-Z][^\n]+?)\s*\n.*?Correct\s*Answer'
            match1 = re.search(pattern1, chunk, re.DOTALL | re.IGNORECASE)
            if match1:
                choice_text = match1.group(1).strip()
                choices[correct_answer] = clean_text(choice_text)
                print(f"  Recovered choice {correct_answer} for question {question_num} (pattern 1)")
                recovered = True
            
            # Pattern 2: Look for corrupted choice marker before "Correct Answer"
            if not recovered:
                last_valid_choice = max(choices.keys()) if choices else 'A'
                recovery_pattern = rf'\n{last_valid_choice}[)\}}].*?\n([^\nA-L]+?)\\s*\nCorrect\s*Answer'
                recovery_match = re.search(recovery_pattern, chunk, re.DOTALL)
                
                if recovery_match:
                    corrupted_line = recovery_match.group(1).strip()
                    # Remove common corruption patterns like "tfil", "tfl", etc.
                    cleaned_corrupted = re.sub(r'^[a-z]+\s*', '', corrupted_line)
                    if cleaned_corrupted:
                        choices[correct_answer] = clean_text(cleaned_corrupted)
                        print(f"  Recovered choice {correct_answer} for question {question_num} (pattern 2)")
                        recovered = True
            
            # Pattern 3: Find text right before Correct Answer that looks like a choice
            if not recovered:
                alt_pattern = r'\n([^\n]+?)\s*\nCorrect\s*Answer\s*:\s*' + correct_answer
                alt_match = re.search(alt_pattern, chunk)
                if alt_match:
                    potential_choice = alt_match.group(1).strip()
                    # Remove any corruption characters at the start
                    potential_choice = re.sub(r'^[a-z]{2,5}\s*', '', potential_choice)
                    # Remove letter prefix if present without parenthesis
                    potential_choice = re.sub(rf'^{correct_answer}\s+', '', potential_choice)
                    # Don't add if it looks like it's part of another choice
                    if potential_choice and not re.match(r'^[A-L][)\}]', potential_choice):
                        choices[correct_answer] = clean_text(potential_choice)
                        print(f"  Recovered choice {correct_answer} for question {question_num} (pattern 3)")
        
        # Extract correct answer explanation
        # Standard format: between "Correct Answer: X." and "Incorrect Answers:"
        explanation_match = re.search(
            r'Correct\s*Answer\s*:\s*[A-L]\.?\s*(.*?)(?=Incorrect\s*Answers?:|lncorrect\s*Answers?:|$)',
            chunk,
            re.DOTALL | re.IGNORECASE
        )
        
        correct_explanation = ""
        if explanation_match:
            correct_explanation = clean_text(explanation_match.group(1))
        else:
            # Try PAREN format: "(X) Explanation text... (A) wrong because..."
            paren_expl_pattern = rf'\({correct_answer}\)\s*([^()]+?)(?=\([A-L]\)|https://|Next Score Report|$)'
            paren_expl_match = re.search(paren_expl_pattern, chunk, re.DOTALL)
            if paren_expl_match:
                correct_explanation = clean_text(paren_expl_match.group(1))
        
        # Extract incorrect answers explanation
        incorrect_match = re.search(
            r'(?:Incorrect\s*Answers?|lncorrect\s*Answers?):\s*([A-L](?:,\s*[A-L])*(?:,?\s*and\s*[A-L])?)\.?\s*(.*?)(?=Exam Section|Next Score Report|https://|$)',
            chunk,
            re.DOTALL | re.IGNORECASE
        )
        
        incorrect_explanation = ""
        if incorrect_match:
            incorrect_explanation = clean_text(incorrect_match.group(2))
        
        # Get system from TOC mapping
        system = system_mapping.get(question_num, "Unknown")
        
        # Build question object
        question = {
            "id": f"{section_code}-{cms_number}-{question_num}",
            "section": SECTION_MAPPINGS.get(section_name, section_name),
            "subsection": f"CMS-{cms_number}",
            "questionNumber": question_num,
            "system": system,
            "questionStem": question_stem,
            "choices": choices,
            "correctAnswer": correct_answer,
            "correctExplanation": correct_explanation,
            "incorrectExplanation": incorrect_explanation
        }
        
        questions.append(question)
    
    return questions


def validate_question(question: dict) -> list[str]:
    """Validate a question dictionary and return list of issues."""
    issues = []
    
    # Check required fields
    required_fields = ["id", "section", "questionStem", "choices", "correctAnswer"]
    for field in required_fields:
        if not question.get(field):
            issues.append(f"Missing required field: {field}")
    
    # Check that correct answer is in choices
    if question.get("correctAnswer") and question.get("choices"):
        if question["correctAnswer"] not in question["choices"]:
            issues.append(f"Correct answer '{question['correctAnswer']}' not in choices")
    
    # Check minimum number of choices
    if question.get("choices") and len(question["choices"]) < 2:
        issues.append(f"Too few choices: {len(question['choices'])}")
    
    # Check for very short question stem (likely parsing error)
    if question.get("questionStem") and len(question["questionStem"]) < 50:
        issues.append(f"Question stem suspiciously short: {len(question['questionStem'])} chars")
    
    # Check for explanation
    if not question.get("correctExplanation"):
        issues.append("Missing correct explanation")
    
    return issues


def process_pdf(pdf_path: str, section_name: str) -> tuple[list[dict], list[str]]:
    """
    Process a single PDF file.
    Returns tuple of (questions list, validation issues list)
    """
    # Extract CMS number from filename (e.g., "3A.pdf" -> "3")
    filename = os.path.basename(pdf_path)
    cms_match = re.match(r'(\d+)A\.pdf', filename)
    if not cms_match:
        return [], [f"Could not parse CMS number from filename: {filename}"]
    
    cms_number = cms_match.group(1)
    
    # Extract text from PDF
    text = extract_pdf_text(pdf_path)
    
    # Parse questions
    questions = parse_questions(text, section_name, cms_number)
    
    # Validate questions
    all_issues = []
    for q in questions:
        issues = validate_question(q)
        if issues:
            all_issues.append(f"Question {q.get('id', 'unknown')}: {'; '.join(issues)}")
    
    return questions, all_issues


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert USMLE Step 2 CK PDFs to JSON")
    parser.add_argument("--cms-dir", default="CMS", help="Directory containing CMS folders")
    parser.add_argument("--output-dir", default="output", help="Output directory for JSON files")
    parser.add_argument("--test", action="store_true", help="Test mode - process only first PDF")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Get absolute paths
    script_dir = Path(__file__).parent.parent
    cms_dir = script_dir / args.cms_dir
    output_dir = script_dir / args.output_dir
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_questions = []
    total_issues = []
    
    # Find all *A.pdf files
    pdf_files = []
    for section_folder in sorted(cms_dir.iterdir()):
        if not section_folder.is_dir():
            continue
        if section_folder.name.startswith('.'):
            continue
            
        for pdf_file in sorted(section_folder.glob("*A.pdf")):
            pdf_files.append((pdf_file, section_folder.name))
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    if args.test:
        pdf_files = pdf_files[:1]
        print("Test mode: processing only first PDF")
    
    # Process each PDF
    for pdf_path, section_name in pdf_files:
        print(f"\nProcessing: {section_name}/{pdf_path.name}")
        
        questions, issues = process_pdf(str(pdf_path), section_name)
        
        print(f"  Extracted {len(questions)} questions")
        
        if issues:
            print(f"  Found {len(issues)} validation issues:")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"    - {issue}")
            if len(issues) > 5:
                print(f"    ... and {len(issues) - 5} more")
            total_issues.extend(issues)
        
        all_questions.extend(questions)
        
        # Save section-specific JSON
        section_output_dir = output_dir / section_name.lower().replace(" ", "_")
        section_output_dir.mkdir(parents=True, exist_ok=True)
        
        cms_number = re.match(r'(\d+)A\.pdf', pdf_path.name).group(1)
        section_json_path = section_output_dir / f"cms_{cms_number}.json"
        
        with open(section_json_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        
        if args.verbose:
            print(f"  Saved to: {section_json_path}")
    
    # Save combined JSON
    combined_path = output_dir / "all_questions.json"
    with open(combined_path, 'w', encoding='utf-8') as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total questions extracted: {len(all_questions)}")
    print(f"Total validation issues: {len(total_issues)}")
    print(f"Combined JSON saved to: {combined_path}")
    
    # Group by section
    section_counts = {}
    for q in all_questions:
        section = q.get("section", "Unknown")
        section_counts[section] = section_counts.get(section, 0) + 1
    
    print("\nQuestions per section:")
    for section, count in sorted(section_counts.items()):
        print(f"  {section}: {count}")
    
    return len(total_issues) == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
