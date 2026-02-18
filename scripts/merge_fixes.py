#!/usr/bin/env python3
"""
Merge manually-edited workbook files back into the parsed JSON output.

Reads each workbook from manual_fixes/, applies non-empty fields to the
corresponding question in Parsed/, and reports what was updated.
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARSED = ROOT / "Parsed"
WORKBOOKS = ROOT / "manual_fixes"

SECTION_CODES = {
    "1_internal_medicine": "IM",
    "2_surgery": "SURG",
    "3_obgyn": "OB",
    "4_pediatrics": "PEDS",
    "5_neurology": "NEURO",
    "6_psychiatry": "PSYCH",
    "7_family_medicine": "FM",
    "8_emergency_medicine": "EM",
}


def is_filled(value) -> bool:
    """Check if a workbook value has been filled in (not empty placeholder)."""
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, dict):
        return any(len(str(v).strip()) > 0 for v in value.values())
    return bool(value)


def merge_workbook(wb_path: Path) -> dict:
    """Merge one workbook into its target JSON. Returns stats."""
    with open(wb_path, encoding="utf-8") as f:
        workbook = json.load(f)

    target_rel = workbook.get("_target", "")
    target_path = ROOT / target_rel
    is_new = workbook.get("_new_file", False)

    fixes = workbook.get("fixes", [])
    if not fixes:
        return {"file": str(wb_path.relative_to(WORKBOOKS)), "updated": 0, "skipped": 0}

    # Load or create target
    if is_new and not target_path.exists():
        cat_slug = target_path.parent.name
        cms_num = target_path.stem.replace("cms_", "")
        section_code = SECTION_CODES.get(cat_slug, "UNK")

        questions = []
        for fix in fixes:
            qn = fix["questionNumber"]
            questions.append({
                "questionNumber": qn,
                "questionStem": None,
                "choices": None,
                "correctAnswer": None,
                "correctExplanation": None,
                "incorrectExplanation": None,
                "image": None,
                "id": f"{section_code}-{cms_num}-{qn}",
                "section": section_code,
                "subsection": f"CMS-{cms_num}",
                "system": None,
            })
    else:
        if not target_path.exists():
            print(f"  WARNING: Target {target_rel} not found, skipping")
            return {"file": str(wb_path.relative_to(WORKBOOKS)), "updated": 0, "skipped": len(fixes)}

        with open(target_path, encoding="utf-8") as f:
            questions = json.load(f)

    q_map = {q["questionNumber"]: q for q in questions}

    updated = 0
    skipped = 0

    for fix in fixes:
        qn = fix["questionNumber"]
        if qn not in q_map:
            if is_new:
                cat_slug = target_path.parent.name
                cms_num = target_path.stem.replace("cms_", "")
                section_code = SECTION_CODES.get(cat_slug, "UNK")
                q_map[qn] = {
                    "questionNumber": qn,
                    "questionStem": None,
                    "choices": None,
                    "correctAnswer": None,
                    "correctExplanation": None,
                    "incorrectExplanation": None,
                    "image": None,
                    "id": f"{section_code}-{cms_num}-{qn}",
                    "section": section_code,
                    "subsection": f"CMS-{cms_num}",
                    "system": None,
                }
                questions.append(q_map[qn])
            else:
                print(f"    Q{qn}: not found in target, skipping")
                skipped += 1
                continue

        q = q_map[qn]
        q_updated = False

        for field in ("questionStem", "choices", "correctAnswer", "correctExplanation"):
            if field not in fix:
                continue
            val = fix[field]

            if not is_filled(val):
                continue

            if field == "choices" and isinstance(val, dict):
                # Filter out empty choice entries
                clean = {k: v.strip() for k, v in val.items() if v and v.strip()}
                if clean:
                    q["choices"] = clean
                    q_updated = True
            else:
                q[field] = val.strip() if isinstance(val, str) else val
                q_updated = True

        # Detect image from stem if newly added
        if q_updated and q.get("questionStem"):
            import re
            img_pattern = re.compile(
                r'(?:shown|pictured|demonstrated|illustrated|see\s+(?:image|figure|photo))',
                re.IGNORECASE,
            )
            if img_pattern.search(q["questionStem"]):
                q["image"] = True

        if q_updated:
            updated += 1
        else:
            skipped += 1

    if updated > 0:
        questions.sort(key=lambda q: q.get("questionNumber", 0))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)

    return {
        "file": str(wb_path.relative_to(WORKBOOKS)),
        "updated": updated,
        "skipped": skipped,
    }


def main():
    if not WORKBOOKS.exists():
        print("No manual_fixes/ directory found. Run generate_workbooks.py first.")
        return

    total_updated = 0
    total_skipped = 0

    for root, dirs, files in sorted(os.walk(WORKBOOKS)):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            wb_path = Path(root) / f

            result = merge_workbook(wb_path)

            if result["updated"] > 0 or result["skipped"] > 0:
                status = f"✓ {result['updated']} updated"
                if result["skipped"]:
                    status += f", {result['skipped']} skipped"
                print(f"  {result['file']}: {status}")

            total_updated += result["updated"]
            total_skipped += result["skipped"]

    print(f"\nDone: {total_updated} questions updated, {total_skipped} skipped")

    # Show new completion stats
    total = 0
    complete = 0
    for root, dirs, files in os.walk(PARSED):
        for f in files:
            if f.startswith("cms_") and f.endswith(".json"):
                with open(os.path.join(root, f), encoding="utf-8") as fh:
                    qs = json.load(fh)
                total += len(qs)
                complete += sum(
                    1 for q in qs
                    if all(q.get(k) for k in
                           ("questionStem", "choices", "correctAnswer",
                            "correctExplanation"))
                )

    print(f"Completion: {complete}/{total} ({complete/total*100:.1f}%)")


if __name__ == "__main__":
    main()
