import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { generateExam, getNextPersonalizedQuestion } from '../utils/generateExam';
import { supabase, isSupabaseConfigured } from '../lib/supabase';
import { useAuth } from './AuthContext';

const ExamContext = createContext(null);

export function ExamProvider({ children }) {
    const { user } = useAuth();
    const [questions, setQuestions] = useState([]);
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [selectedAnswer, setSelectedAnswer] = useState(null);
    const [struckThroughChoices, setStruckThroughChoices] = useState(new Set());
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [answeredQuestions, setAnsweredQuestions] = useState(new Map());
    const [loading, setLoading] = useState(true);
    const [isPersonalizedMode, setIsPersonalizedMode] = useState(false);
    const [examConfig, setExamConfig] = useState(null);
    const [userProgress, setUserProgress] = useState([]);

    // Load questions based on config from sessionStorage
    useEffect(() => {
        loadExam();
    }, [user]);

    const loadExam = async () => {
        setLoading(true);

        const configStr = sessionStorage.getItem('examConfig');
        if (!configStr) {
            // Default to all questions if no config
            const defaultConfig = {
                subjects: ['Internal Medicine', 'Surgery', 'OB/GYN', 'Pediatrics', 'Neurology', 'Psychiatry', 'Family Medicine', 'Emergency Medicine'],
                mode: 'all',
                count: 20
            };
            sessionStorage.setItem('examConfig', JSON.stringify(defaultConfig));
        }

        const config = JSON.parse(sessionStorage.getItem('examConfig'));
        setExamConfig(config);
        setIsPersonalizedMode(config.mode === 'personalized');

        // Fetch user progress for filtering
        let progress = [];
        if (isSupabaseConfigured() && supabase && user) {
            try {
                // Add timeout to prevent hanging
                const timeoutPromise = new Promise((resolve) =>
                    setTimeout(() => resolve({ data: [] }), 3000)
                );

                const fetchPromise = supabase
                    .from('user_progress')
                    .select('question_id, correct')
                    .eq('user_id', user.id);

                const result = await Promise.race([fetchPromise, timeoutPromise]);
                progress = result.data || [];
            } catch (err) {
                console.error('Error fetching progress:', err);
                progress = [];
            }
        }
        setUserProgress(progress);

        const examQuestions = generateExam(config, progress);
        setQuestions(examQuestions);
        setCurrentQuestionIndex(0);
        setSelectedAnswer(null);
        setIsSubmitted(false);
        setStruckThroughChoices(new Set());
        setAnsweredQuestions(new Map());
        setLoading(false);
    };

    const currentQuestion = questions[currentQuestionIndex];

    const selectAnswer = useCallback((choice) => {
        if (!isSubmitted) {
            setSelectedAnswer(choice);
        }
    }, [isSubmitted]);

    const toggleStrikethrough = useCallback((choice) => {
        if (!isSubmitted) {
            setStruckThroughChoices(prev => {
                const next = new Set(prev);
                if (next.has(choice)) {
                    next.delete(choice);
                } else {
                    next.add(choice);
                }
                return next;
            });
        }
    }, [isSubmitted]);

    const submit = useCallback(async () => {
        if (selectedAnswer && !isSubmitted && currentQuestion) {
            const isCorrect = selectedAnswer === currentQuestion.correctAnswer;

            setIsSubmitted(true);
            setAnsweredQuestions(prev => {
                const next = new Map(prev);
                next.set(currentQuestion.id, {
                    selected: selectedAnswer,
                    correct: isCorrect
                });
                return next;
            });

            // Persist to Supabase
            if (isSupabaseConfigured() && supabase && user) {
                try {
                    await supabase.from('user_progress').insert({
                        user_id: user.id,
                        question_id: currentQuestion.id,
                        section: currentQuestion.section,
                        correct: isCorrect,
                        answer_selected: selectedAnswer
                    });

                    // Update local progress for personalized mode
                    setUserProgress(prev => [...prev, {
                        question_id: currentQuestion.id,
                        correct: isCorrect
                    }]);
                } catch (err) {
                    console.error('Error saving progress:', err);
                }
            }
        }
    }, [selectedAnswer, isSubmitted, currentQuestion, user]);

    // For personalized mode: get next question after submission
    const getNextPersonalized = useCallback(async () => {
        if (!isPersonalizedMode || !examConfig) return;

        // Fetch fresh progress
        let progress = userProgress;
        if (isSupabaseConfigured() && supabase && user) {
            try {
                const { data } = await supabase
                    .from('user_progress')
                    .select('question_id, correct')
                    .eq('user_id', user.id);
                progress = data || [];
                setUserProgress(progress);
            } catch (err) {
                console.error('Error fetching progress:', err);
            }
        }

        const nextQuestion = getNextPersonalizedQuestion(examConfig.subjects, progress);
        if (nextQuestion) {
            setQuestions([nextQuestion]);
            setCurrentQuestionIndex(0);
            setSelectedAnswer(null);
            setIsSubmitted(false);
            setStruckThroughChoices(new Set());
        }
    }, [isPersonalizedMode, examConfig, userProgress, user]);

    const goToQuestion = useCallback((index) => {
        if (index >= 0 && index < questions.length) {
            setCurrentQuestionIndex(index);

            // Load previous state for this question
            const prevAnswer = answeredQuestions.get(questions[index].id);
            if (prevAnswer) {
                setSelectedAnswer(prevAnswer.selected);
                setIsSubmitted(true);
            } else {
                setSelectedAnswer(null);
                setIsSubmitted(false);
            }
            setStruckThroughChoices(new Set());
        }
    }, [questions, answeredQuestions]);

    const nextQuestion = useCallback(() => {
        if (isPersonalizedMode) {
            getNextPersonalized();
        } else {
            goToQuestion(currentQuestionIndex + 1);
        }
    }, [currentQuestionIndex, goToQuestion, isPersonalizedMode, getNextPersonalized]);

    const prevQuestion = useCallback(() => {
        goToQuestion(currentQuestionIndex - 1);
    }, [currentQuestionIndex, goToQuestion]);

    const getProgress = useCallback((sectionQuestions) => {
        let completed = 0;
        for (const q of sectionQuestions) {
            if (answeredQuestions.has(q.id)) {
                completed++;
            }
        }
        return { completed, total: sectionQuestions.length };
    }, [answeredQuestions]);

    const value = {
        questions,
        currentQuestion,
        currentQuestionIndex,
        selectedAnswer,
        struckThroughChoices,
        isSubmitted,
        answeredQuestions,
        loading,
        isPersonalizedMode,
        selectAnswer,
        toggleStrikethrough,
        submit,
        goToQuestion,
        nextQuestion,
        prevQuestion,
        getProgress,
        getNextPersonalized
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-gray-50">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-gray-600">Loading exam...</p>
                </div>
            </div>
        );
    }

    if (questions.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <p className="text-gray-600 mb-4">No questions match your criteria.</p>
                    <a href="/exam/config" className="text-blue-600 hover:underline">
                        Go back and adjust your filters
                    </a>
                </div>
            </div>
        );
    }

    return (
        <ExamContext.Provider value={value}>
            {children}
        </ExamContext.Provider>
    );
}

export function useExam() {
    const context = useContext(ExamContext);
    if (!context) {
        throw new Error('useExam must be used within an ExamProvider');
    }
    return context;
}
