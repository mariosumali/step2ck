import { createClient } from '@supabase/supabase-js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Section name mappings
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

// Read .env file
const envPath = path.resolve(__dirname, '.env');
const envConfig = {};

try {
    const envFile = fs.readFileSync(envPath, 'utf8');
    envFile.split('\n').forEach(line => {
        const [key, value] = line.split('=');
        if (key && value) {
            envConfig[key.trim()] = value.trim();
        }
    });
} catch (e) {
    console.error('Could not read .env file:', e.message);
    process.exit(1);
}

const supabaseUrl = envConfig.VITE_SUPABASE_URL;
const supabaseKey = envConfig.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Supabase credentials missing in .env');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

function normalizeSection(section) {
    const normalized = SECTION_MAP[section];
    if (!normalized) {
        console.warn(`Unknown section: ${section}, keeping as-is`);
        return section;
    }
    return normalized;
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
        question_number: q.questionNumber || null,
        system: q.system || null,
        question_stem: q.questionStem,
        choices: q.choices,
        correct_answer: q.correctAnswer,
        correct_explanation: q.correctExplanation || null,
        incorrect_explanation: q.incorrectExplanation || null
    };
}

async function seed() {
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

    const sectionCounts = {};
    for (const q of questionsArray) {
        sectionCounts[q.section] = (sectionCounts[q.section] || 0) + 1;
    }
    console.log('Questions by section:', sectionCounts);

    const batchSize = 50;
    let uploaded = 0;
    let errors = 0;

    for (let i = 0; i < questionsArray.length; i += batchSize) {
        const batch = questionsArray.slice(i, i + batchSize);

        const { error } = await supabase
            .from('questions')
            .upsert(batch, { onConflict: 'id' });

        if (error) {
            console.error(`Batch ${i / batchSize + 1} error:`, error.message);
            errors += batch.length;
        } else {
            uploaded += batch.length;
            console.log(`Uploaded batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(questionsArray.length / batchSize)}`);
        }
    }

    console.log(`\nDone! Uploaded ${uploaded} questions, ${errors} errors`);
}

seed().catch(console.error);
