#!/usr/bin/env python3
"""
Generate fill-in workbook JSON files for manual fixes.
Each workbook corresponds to one parsed JSON file and contains only
the questions that need manual attention, with clear placeholders.

Run merge_fixes.py after editing to apply changes back.
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARSED = ROOT / "Parsed"
CMS = ROOT / "CMS"
WORKBOOKS = ROOT / "manual_fixes"

SLUG_TO_CMS = {
    "1_internal_medicine": "1 Internal Medicine",
    "2_surgery": "2 Surgery",
    "3_obgyn": "3 OBGYN",
    "4_pediatrics": "4 Pediatrics",
    "5_neurology": "5 Neurology",
    "6_psychiatry": "6 Psychiatry",
    "7_family_medicine": "7 Family Medicine",
    "8_emergency_medicine": "8 Emergency Medicine",
}


def truncate(s: str, n: int = 120) -> str:
    if not s:
        return ""
    return s[:n] + ("..." if len(s) > n else "")


def generate_workbooks():
    WORKBOOKS.mkdir(parents=True, exist_ok=True)
    total_fixes = 0
    files_created = 0

    for cat_slug in sorted(os.listdir(PARSED)):
        cat_dir = PARSED / cat_slug
        if not cat_dir.is_dir() or cat_slug not in SLUG_TO_CMS:
            continue

        cms_name = SLUG_TO_CMS[cat_slug]

        for fname in sorted(os.listdir(cat_dir)):
            if not (fname.startswith("cms_") and fname.endswith(".json")):
                continue

            num = fname.replace("cms_", "").replace(".json", "")
            json_path = cat_dir / fname

            with open(json_path, encoding="utf-8") as f:
                questions = json.load(f)

            fixes = []
            for q in questions:
                missing_fields = []
                if not q.get("questionStem"):
                    missing_fields.append("questionStem")
                if not q.get("choices"):
                    missing_fields.append("choices")
                if not q.get("correctAnswer"):
                    missing_fields.append("correctAnswer")
                if not q.get("correctExplanation"):
                    missing_fields.append("correctExplanation")

                if not missing_fields:
                    continue

                entry = {"questionNumber": q["questionNumber"]}

                # Context: show existing fields so user knows which question this is
                context = {}
                if q.get("questionStem"):
                    context["stem_preview"] = truncate(q["questionStem"])
                if q.get("correctAnswer"):
                    context["correctAnswer"] = q["correctAnswer"]
                if q.get("choices"):
                    context["existing_choices"] = list(q["choices"].keys())
                if context:
                    entry["_context"] = context

                # Placeholders for missing fields
                for field in missing_fields:
                    if field == "choices":
                        entry["choices"] = {"A": "", "B": "", "C": "", "D": "", "E": ""}
                    elif field == "questionStem":
                        entry["questionStem"] = ""
                    elif field == "correctAnswer":
                        entry["correctAnswer"] = ""
                    elif field == "correctExplanation":
                        entry["correctExplanation"] = ""

                fixes.append(entry)

            if not fixes:
                continue

            # Determine source PDF
            a_pdf = f"CMS/{cms_name}/{num}A.pdf"
            q_pdf = f"CMS/{cms_name}/{num} Q.pdf"

            workbook = {
                "_instructions": (
                    "Fill in the empty strings (\"\") below. "
                    "Delete any entries you want to skip. "
                    "Then run:  python3 scripts/merge_fixes.py"
                ),
                "_source_pdf": a_pdf,
                "_q_pdf": q_pdf if (ROOT / q_pdf).exists() else None,
                "_target": str(json_path.relative_to(ROOT)),
                "fixes": fixes,
            }

            # Remove null _q_pdf
            if workbook["_q_pdf"] is None:
                del workbook["_q_pdf"]

            wb_dir = WORKBOOKS / cat_slug
            wb_dir.mkdir(parents=True, exist_ok=True)
            wb_path = wb_dir / fname

            with open(wb_path, "w", encoding="utf-8") as f:
                json.dump(workbook, f, indent=2, ensure_ascii=False)

            total_fixes += len(fixes)
            files_created += 1
            print(f"  {cat_slug}/{fname}: {len(fixes)} questions to fix")

    # Also create templates for completely missing files
    missing_files = [
        ("7_family_medicine", "7 Family Medicine", "5", 50),
        ("8_emergency_medicine", "8 Emergency Medicine", "3", 50),
    ]

    for slug, cms_name, num, expected_count in missing_files:
        json_path = PARSED / slug / f"cms_{num}.json"
        if json_path.exists():
            continue

        fixes = []
        for i in range(1, expected_count + 1):
            fixes.append({
                "questionNumber": i,
                "questionStem": "",
                "choices": {"A": "", "B": "", "C": "", "D": "", "E": ""},
                "correctAnswer": "",
                "correctExplanation": "",
            })

        workbook = {
            "_instructions": (
                "This file is ENTIRELY MISSING from parsed output. "
                "Fill in all fields. The source PDF is image-only. "
                "Then run:  python3 scripts/merge_fixes.py"
            ),
            "_source_pdf": f"CMS/{cms_name}/{num}A.pdf",
            "_q_pdf": f"CMS/{cms_name}/{num} Q.pdf",
            "_target": f"Parsed/{slug}/cms_{num}.json",
            "_new_file": True,
            "fixes": fixes,
        }

        wb_dir = WORKBOOKS / slug
        wb_dir.mkdir(parents=True, exist_ok=True)
        wb_path = wb_dir / f"cms_{num}.json"

        with open(wb_path, "w", encoding="utf-8") as f:
            json.dump(workbook, f, indent=2, ensure_ascii=False)

        total_fixes += expected_count
        files_created += 1
        print(f"  {slug}/cms_{num}.json: {expected_count} questions (NEW FILE)")

    print(f"\nGenerated {files_created} workbooks in manual_fixes/")
    print(f"Total questions needing fixes: {total_fixes}")
    print(f"\nWorkflow:")
    print(f"  1. Open a workbook from manual_fixes/")
    print(f"  2. Open the source PDF side-by-side")
    print(f"  3. Fill in the empty strings")
    print(f"  4. Run: python3 scripts/merge_fixes.py")


if __name__ == "__main__":
    generate_workbooks()
