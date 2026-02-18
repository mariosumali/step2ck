import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const SECTION_MAP = {
    'IM': 'Internal Medicine',
    'SUR': 'Surgery',
    'SURG': 'Surgery',
    'OB': 'OB/GYN',
    'OBGYN': 'OB/GYN',
    'PED': 'Pediatrics',
    'PEDS': 'Pediatrics',
    'NEURO': 'Neurology',
    'PSYCH': 'Psychiatry',
    'FM': 'Family Medicine',
    'EM': 'Emergency Medicine',
    'Internal Medicine': 'Internal Medicine',
    'Surgery': 'Surgery',
    'OB/GYN': 'OB/GYN',
    'Pediatrics': 'Pediatrics',
    'Neurology': 'Neurology',
    'Psychiatry': 'Psychiatry',
    'Family Medicine': 'Family Medicine',
    'Emergency Medicine': 'Emergency Medicine'
};

function normalizeSection(section) {
    return SECTION_MAP[section] || section;
}

function findAllJsonFiles(dir) {
    const files = [];
    const items = fs.readdirSync(dir, { withFileTypes: true });

    for (const item of items) {
        const fullPath = path.join(dir, item.name);
        if (item.isDirectory()) {
            files.push(...findAllJsonFiles(fullPath));
        } else if (item.name.endsWith('.json') && item.name !== 'all_questions.json') {
            files.push(fullPath);
        }
    }

    return files;
}

function cleanQuestion(q) {
    if (!q.questionStem || q.questionStem.length < 20) return null;
    if (!q.choices || Object.keys(q.choices).length === 0) return null;
    if (!q.correctAnswer) return null;

    return {
        id: q.id,
        section: normalizeSection(q.section),
        subsection: q.subsection || null,
        questionNumber: q.questionNumber || null,
        system: q.system || null,
        questionStem: q.questionStem,
        choices: q.choices,
        correctAnswer: q.correctAnswer,
        correctExplanation: q.correctExplanation || null,
        incorrectExplanation: q.incorrectExplanation || null
    };
}

const outputDir = path.resolve(__dirname, '../output');
const jsonFiles = findAllJsonFiles(outputDir);

console.log(`Found ${jsonFiles.length} JSON files`);

const allQuestions = new Map();
let skipped = 0;

for (const file of jsonFiles) {
    try {
        const content = fs.readFileSync(file, 'utf8');
        const questions = JSON.parse(content);

        if (!Array.isArray(questions)) continue;

        for (const q of questions) {
            const cleaned = cleanQuestion(q);
            if (cleaned && cleaned.id) {
                if (!allQuestions.has(cleaned.id)) {
                    allQuestions.set(cleaned.id, cleaned);
                }
            } else {
                skipped++;
            }
        }
    } catch (err) {
        console.error(`Error reading ${file}:`, err.message);
    }
}

const questionsArray = Array.from(allQuestions.values());
console.log(`Prepared ${questionsArray.length} unique questions (skipped ${skipped} invalid)`);

// Count by section
const sectionCounts = {};
for (const q of questionsArray) {
    sectionCounts[q.section] = (sectionCounts[q.section] || 0) + 1;
}
console.log('Questions by section:', sectionCounts);

// Write to all_questions.json
const outputPath = path.resolve(__dirname, '../output/all_questions.json');
fs.writeFileSync(outputPath, JSON.stringify(questionsArray, null, 2));
console.log(`\nWritten to ${outputPath}`);
