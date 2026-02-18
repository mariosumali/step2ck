/**
 * Data cleaning utility for messy scraped exam data
 * Handles artifacts like leading "nd X." prefixes, trailing dashes, and navigation text
 */

/**
 * Clean explanation text by removing common artifacts
 * @param {string} text - Raw explanation text from scraped data
 * @returns {string} - Cleaned text ready for display
 */
export function cleanExplanation(text) {
    if (!text || typeof text !== 'string') {
        return '';
    }

    let cleaned = text;

    // Remove leading "nd X." patterns (e.g., "nd E.", "nd A.", "nd C.")
    cleaned = cleaned.replace(/^nd\s+[A-G]\.\s*/i, '');

    // Remove trailing navigation text patterns
    const navPatterns = [
        /\s*Previous\s*$/i,
        /\s*Next\s*$/i,
        /\s*Score\s*Report\s*$/i,
        /\s*Lab\s*Values\s*$/i,
        /\s*Calculator\s*$/i,
        /\s*Help\s*$/i,
        /\s*Pause\s*$/i,
        /\s*https?:\/\/[^\s]+\s*$/i,
    ];

    for (const pattern of navPatterns) {
        cleaned = cleaned.replace(pattern, '');
    }

    // Remove trailing sequences of dashes with optional spaces
    // Matches patterns like "- - - -", "---", "- - - - - - -"
    cleaned = cleaned.replace(/[\s-]*[-\s]{3,}[\s-]*$/g, '');

    // Remove standalone dash sequences in the middle (artifact lines)
    cleaned = cleaned.replace(/\s*-\s*-\s*-[\s-]*/g, ' ');

    // Remove various OCR artifacts
    cleaned = cleaned.replace(/r\s*~,\s*~\s*~\s*r,/g, '');
    cleaned = cleaned.replace(/~,\s*~\s*~\s*r,/g, '');

    // Clean up multiple spaces
    cleaned = cleaned.replace(/\s{2,}/g, ' ');

    // Trim whitespace
    cleaned = cleaned.trim();

    return cleaned;
}

/**
 * Clean question stem text
 * @param {string} text - Raw question stem
 * @returns {string} - Cleaned question stem
 */
export function cleanQuestionStem(text) {
    if (!text || typeof text !== 'string') {
        return '';
    }

    let cleaned = text;

    // Remove OCR artifacts with extra spaces in words
    // This handles cases like "hypertens ion" -> "hypertension"
    // Note: Being conservative here to avoid breaking legitimate text

    // Clean up multiple spaces
    cleaned = cleaned.replace(/\s{2,}/g, ' ');

    return cleaned.trim();
}

/**
 * Clean choice text
 * @param {string} text - Raw choice text
 * @returns {string} - Cleaned choice text
 */
export function cleanChoiceText(text) {
    if (!text || typeof text !== 'string') {
        return '';
    }

    let cleaned = text;

    // Remove trailing artifacts like "~-" or similar
    cleaned = cleaned.replace(/\s*~[-~]*\s*$/g, '');
    cleaned = cleaned.replace(/\s*[;-]+\s*$/g, '');

    // Clean up multiple spaces
    cleaned = cleaned.replace(/\s{2,}/g, ' ');

    return cleaned.trim();
}
