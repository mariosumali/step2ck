# CMS PDF Question Parser — Plan

## Audit Summary

After inspecting every folder, existing scripts, prior outputs, and sample PDFs from each type, here's the landscape.

**8 categories** across `CMS/`, each with a mix of Q and A PDFs:

| Category | Official NBME A PDFs | Community A PDFs | Q-only (no A) |
|---|---|---|---|
| 1 Internal Medicine | 3A–8A (6) | none | 1Q, 2Q |
| 2 Surgery | 3A–8A (6) | 1A, 2A | — |
| 3 OBGYN | 3A–8A (6) | 1A, 2A | — |
| 4 Pediatrics | 3A–8A (6) | 1A | — |
| 5 Neurology | 3A–8A (6) | 1A, 2A | — |
| 6 Psychiatry | 3A–7A (5) | 1A | 2Q |
| 7 Family Medicine | 3A–5A (3) | 1A, 2A | — |
| 8 Emergency Medicine | 3A (1) | 1A, 2A | — |

### Three Distinct PDF Formats

1. **Official NBME A PDFs** (forms 3+): Scanned screenshots of the NBME CMS interface. Contain full question stems, choices, correct answer, correct/incorrect explanations, and a table of contents mapping questions to organ systems. This is the richest source. *Most* are image-based (text extraction yields only watermark URLs), though some yield partial text with OCR artifacts like `tfil` instead of `E)` and `SY.stem` instead of `System`.

2. **Community A PDFs** (forms 1–2): Hand-written student answer keys. Format is just `1. D. Brief explanation...`. These have the correct answer letter and a short explanation, but **no question stem and no choices**. These were entirely skipped in the previous parsing run.

3. **Q-only PDFs**: Screen-captured questions with no corresponding answer key at all (IM 1Q, IM 2Q, Psychiatry 2Q). These should be skipped for now.

### Previous Run Results (in `output/`)

- Used GPT-4o Vision per-page via `pdf_parser_gpt.py`
- Processed ~39 official NBME PDFs (skipped all community answer keys)
- Hit rate limits (429 errors) on larger PDFs (100+ pages), causing ~5–15 missing questions per large PDF
- No image detection was done
- No `system` field was populated for Vision-parsed PDFs

---

## Proposed Architecture

A **single new Python script** (`scripts/parse_cms.py`) with three parsing strategies, image detection, and comprehensive reporting. Output goes to a new `Parsed/` folder.

### Phase 1: PDF Discovery & Classification

Walk the `CMS/` directory tree and classify every PDF:

- If `XA.pdf` exists and contains "Exam Section" or has NBME page structure → **Official NBME**
- If `XA.pdf` exists but is a community answer key (detect by absence of "Exam Section" and presence of patterns like `1. A)` or `Right answer is`) → **Community**
- If only `X Q.pdf` exists with no corresponding A → **Q-only (skip)**

### Phase 2: Parsing Strategies

**Strategy A — Text Extraction (Official NBME, text-extractable):**

- Use `pypdf` to extract text
- Improved regex from the existing `pdf_parser.py` (fix OCR artifact handling)
- Parse: TOC/system mapping, question stem, choices, correct answer, explanations
- Fastest & cheapest — no API calls needed

**Strategy B — Vision AI (Official NBME, image-only):**

- For PDFs where text extraction yields only watermarks/no content
- Convert PDF pages to images with `pdf2image`
- Send to GPT-4o Vision with a structured extraction prompt
- Key improvements over previous run:
  - Exponential backoff with jitter on 429 errors (retry up to 5x)
  - Rate-limit-aware concurrency (2 parallel requests max, configurable delay)
  - Request both question data AND whether the page contains an image in a single call
  - Resume capability: skip PDFs that already have output files

**Strategy C — Community PDF Parser (community A PDFs):**

- Different regex patterns for each community format variant:
  - `N. LETTER. Explanation` (Surgery style)
  - `Right answer is LETTER` + explanation paragraphs (Psychiatry style)
  - Bullet-point format with `• explanation` (Surgery 1A style)
- Extract: `questionNumber`, `correctAnswer`, `correctExplanation`, `incorrectExplanation`
- Leave as `null`: `questionStem`, `choices`, `system`
- These are **partial records** — the report will flag them

### Phase 3: Image Detection

Scan the `questionStem` text for phrases indicating an associated image. Heuristic patterns:

- `"is shown"`, `"are shown"`, `"shown here"`, `"shown in the"`
- `"photograph"`, `"photomicrograph"`, `"gross appearance"`
- `"x-ray"`, `"radiograph"`, `"CT scan"`, `"MRI"`, `"ultrasound"`, `"echocardiogram"`
- `"biopsy specimen"`, `"microscopic"`, `"histologic"`
- `"figure"`, `"image"`, `"the slide"`

If any of these patterns are found, set `"image": true`. Otherwise `"image": null` (not `false`, since we can't be certain from text alone that there's no image — especially for community PDFs where we don't have the stem).

For Vision AI parsing (Strategy B), GPT-4o can directly see and report whether the page contains a clinical image.

### Phase 3.5: Post-Extraction Validation (Lightweight)

Every extracted question runs through cheap, zero-API-call heuristics to flag likely problems. These checks run on the already-extracted text and add negligible processing time.

**Truncation detection** (for `correctExplanation`, `incorrectExplanation`, `questionStem`):

- **Incomplete sentence**: Text ends without terminal punctuation (`.`, `?`, `!`). Ending on a comma, conjunction (`and`, `or`, `but`), preposition, or article is a strong truncation signal.
- **Unbalanced delimiters**: Unclosed parentheses `(`, quotation marks `"`, or brackets `[` — common when a page boundary cut the text mid-thought.
- **Trailing UI artifacts**: Text ends with fragments of the NBME interface chrome (e.g., `Previous`, `Next`, `Score Report`, `Lab Values`, `Calculator`, `Help`, `Pause`) or watermark URLs (`t.me/`). These should be stripped, and if stripping them leaves an incomplete sentence, flag it.
- **Suspiciously short**: `correctExplanation` under 80 characters or `incorrectExplanation` under 50 characters is likely truncated or missing content, since NBME explanations are typically multi-sentence.

**Content integrity checks**:

- **Correct answer not in choices**: If `correctAnswer` is `"E"` but `choices` only has A–D, the extraction missed a choice (common OCR failure for the last option).
- **Duplicate choice text**: Two choices with identical text suggests a parsing error.
- **Question number gap**: If a PDF has questions 1–50 but the parser only found 45, flag which numbers are missing.
- **Choice count sanity**: Most NBME questions have 5 choices (A–E). Fewer than 3 or more than 10 is unusual and worth flagging.

**Severity levels**:

Each issue gets a severity that determines how it appears in the report:
- `error` — almost certainly wrong (e.g., correct answer not in choices, question missing entirely)
- `warning` — likely truncated or malformed (e.g., explanation ends mid-sentence, suspiciously short)
- `info` — unusual but possibly fine (e.g., only 3 choices, very long explanation)

These all feed into `parse_report.json` under a `"validationIssues"` array per question, so you can filter/sort by severity without re-running anything.

### Phase 4: Output Schema

Each question follows this format:

```json
{
  "questionNumber": 1,
  "questionStem": "A 19-year-old woman comes for...",
  "choices": {"A": "Chronic migraines", "B": "Early cataracts", ...},
  "correctAnswer": "E",
  "correctExplanation": "Isotretinoin (retinoic acid)...",
  "incorrectExplanation": "Chronic migraines, early cataracts...",
  "image": null,
  "id": "IM-3-1",
  "section": "IM",
  "subsection": "CMS-3",
  "system": "Musculoskeletal, Skin, & Subcutaneous Tissue"
}
```

Any field that can't be extracted gets `null`.

### Phase 5: Output Structure

```
Parsed/
├── 1_internal_medicine/
│   ├── cms_3.json
│   ├── cms_4.json
│   ├── cms_5.json
│   ├── cms_6.json
│   ├── cms_7.json
│   └── cms_8.json
├── 2_surgery/
│   ├── cms_1.json          (partial — community PDF)
│   ├── cms_2.json          (partial — community PDF)
│   ├── cms_3.json ... cms_8.json
├── ... (same pattern for categories 3–8)
├── all_questions.json       (combined)
└── parse_report.json
```

### Phase 6: Report Generation

`parse_report.json` containing:

```json
{
  "summary": {
    "totalPdfsFound": 63,
    "totalPdfsParsed": 56,
    "totalPdfsSkipped": 3,
    "totalQuestions": 2800,
    "totalComplete": 2500,
    "totalPartial": 300,
    "totalWithImages": 150
  },
  "byCategory": { "..." : "..." },
  "skippedPdfs": [
    {"pdf": "1 Internal Medicine/1 Q.pdf", "reason": "Q-only, no answer key"}
  ],
  "partialPdfs": [
    {"pdf": "2 Surgery/1A.pdf", "reason": "Community answer key (no question stems/choices)", "questionsFound": 50}
  ],
  "missingFields": [
    {"id": "SURG-1-1", "missing": ["questionStem", "choices", "system"]},
    {"id": "IM-7-66", "missing": ["correctExplanation"], "reason": "API rate limit"}
  ],
  "validationIssues": [
    {"id": "SURG-3-12", "severity": "error", "issue": "correctAnswer 'E' not found in choices (A-D only)"},
    {"id": "IM-5-31", "severity": "warning", "issue": "correctExplanation appears truncated (ends with ', and')"},
    {"id": "NEURO-4-8", "severity": "warning", "issue": "incorrectExplanation ends with UI artifact 'Previous Next Score Report'"},
    {"id": "OB-6-22", "severity": "warning", "issue": "correctExplanation suspiciously short (47 chars)"},
    {"id": "PEDS-3-1", "severity": "info", "issue": "Only 3 choices found (unusual)"}
  ],
  "questionGaps": [
    {"pdf": "1 Internal Medicine/7A.pdf", "expected": 50, "found": 43, "missing": [12, 17, 25, 33, 38, 44, 49]}
  ],
  "errors": []
}
```

---

## Open Questions / Decision Points

1. **Community A PDFs** — should we parse them now (with many null fields) or skip them entirely and come back later? Parsing them gives us at least the answer letter + explanation for ~150–200 questions, but they'll be heavily incomplete records. Depending on what percent of the files they take, we should skip them or try to parse them. 

2. **Existing `output/` data** — should the new script ignore the prior run's data entirely, or could we use it as a validation baseline or even merge/backfill from it? Do what you would consider to be best. But the priority is that all the questions are correctly parsed. 

3. **GPT-4o cost/rate limits** — the previous run used ~39 PDFs × ~60 pages average × ~$0.01–0.03 per page. A full re-run of the image-based PDFs could cost $20–60. Should we:

   - Only re-run PDFs with missing questions from rate limits
   - Try text extraction first and only fall back to Vision AI when needed? Do the this one. But also do a robust check for any issues with the previous run. 

4. **Image handling** — when Vision AI detects an actual image on the page, should we extract/save the image file too, or just flag `"image": true`? Saving images would require additional storage and processing. We should save images. 

5. **`Sample Items` folder** — there are 10 PDFs in `CMS/Sample Items/`. Should these be parsed too, or excluded? Sample items differe because all the answers are present on the last page and the questions are all sequential. These should also be parsed with these additional considerations in mind. 
