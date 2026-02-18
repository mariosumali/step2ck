import allQuestions from '../../../output/all_questions.json';

/**
 * Generate a shuffled subset of questions based on configuration
 * @param {Object} config - Exam configuration
 * @param {string[]} config.subjects - Array of selected subject names
 * @param {'all' | 'unused' | 'incorrect' | 'personalized'} config.mode - Question filter mode
 * @param {number} config.count - Number of questions to return
 * @param {Object[]} userProgress - User's progress data from Supabase
 * @returns {Object[]} Shuffled array of questions
 */
export function generateExam(config, userProgress = []) {
    const { subjects, mode, count } = config;

    // Filter by selected subjects
    let filtered = allQuestions.filter(q => subjects.includes(q.section));

    // Apply mode filter
    if (mode === 'unused') {
        const answeredIds = new Set(userProgress.map(p => p.question_id));
        filtered = filtered.filter(q => !answeredIds.has(q.id));
    } else if (mode === 'incorrect') {
        const incorrectIds = new Set(
            userProgress.filter(p => !p.correct).map(p => p.question_id)
        );
        filtered = filtered.filter(q => incorrectIds.has(q.id));
    } else if (mode === 'personalized') {
        // Personalized mode: prioritize unused and incorrect questions
        filtered = generatePersonalizedQueue(filtered, userProgress);
        // Return just the first question for personalized mode
        return filtered.slice(0, count);
    }

    // Shuffle using Fisher-Yates algorithm
    const shuffled = [...filtered];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }

    // Return requested count
    return shuffled.slice(0, count);
}

/**
 * Generate a personalized question queue
 * Priority: 1. Never seen questions, 2. Incorrect questions, 3. Correct questions (least recent first)
 * @param {Object[]} questions - Filtered questions by subject
 * @param {Object[]} userProgress - User's progress data
 * @returns {Object[]} Prioritized and shuffled questions
 */
function generatePersonalizedQueue(questions, userProgress) {
    // Create maps for quick lookup
    const progressMap = new Map();
    const incorrectCounts = new Map();

    userProgress.forEach(p => {
        // Track whether question was answered
        if (!progressMap.has(p.question_id)) {
            progressMap.set(p.question_id, { answered: true, correct: p.correct });
        }

        // Track incorrect count for priority scoring
        if (!p.correct) {
            incorrectCounts.set(p.question_id, (incorrectCounts.get(p.question_id) || 0) + 1);
        }
    });

    // Categorize questions
    const neverSeen = [];
    const incorrectQuestions = [];
    const correctQuestions = [];

    questions.forEach(q => {
        const progress = progressMap.get(q.id);

        if (!progress) {
            neverSeen.push(q);
        } else if (!progress.correct) {
            // Add priority score based on how many times incorrect
            incorrectQuestions.push({
                ...q,
                _priority: incorrectCounts.get(q.id) || 1
            });
        } else {
            correctQuestions.push(q);
        }
    });

    // Shuffle each category
    const shuffle = (arr) => {
        const shuffled = [...arr];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    };

    // Sort incorrect by priority (most incorrect first), then shuffle within same priority
    incorrectQuestions.sort((a, b) => b._priority - a._priority);

    // Combine: never seen (shuffled) + incorrect (by priority) + correct (shuffled)
    return [
        ...shuffle(neverSeen),
        ...incorrectQuestions,
        ...shuffle(correctQuestions)
    ];
}

/**
 * Get the next personalized question
 * @param {string[]} subjects - Selected subjects
 * @param {Object[]} userProgress - User's progress data
 * @returns {Object|null} Next question or null if none available
 */
export function getNextPersonalizedQuestion(subjects, userProgress) {
    const filtered = allQuestions.filter(q => subjects.includes(q.section));
    const queue = generatePersonalizedQueue(filtered, userProgress);
    return queue[0] || null;
}

/**
 * Get all questions from the master JSON
 */
export function getAllQuestions() {
    return allQuestions;
}

/**
 * Get unique sections from all questions
 */
export function getSections() {
    const sections = new Set(allQuestions.map(q => q.section));
    return Array.from(sections);
}
