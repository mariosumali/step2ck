import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, ChevronLeft, Check, Sparkles, Zap } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../context/AuthContext';
import allQuestions from '../../../output/all_questions.json';

const SUBJECTS = [
    { id: 'Internal Medicine', label: 'Internal Medicine', color: 'bg-blue-500' },
    { id: 'Surgery', label: 'Surgery', color: 'bg-red-500' },
    { id: 'OB/GYN', label: 'OB/GYN', color: 'bg-pink-500' },
    { id: 'Pediatrics', label: 'Pediatrics', color: 'bg-amber-500' },
    { id: 'Neurology', label: 'Neurology', color: 'bg-purple-500' },
    { id: 'Psychiatry', label: 'Psychiatry', color: 'bg-cyan-500' },
    { id: 'Family Medicine', label: 'Family Medicine', color: 'bg-emerald-500' },
    { id: 'Emergency Medicine', label: 'Emergency Medicine', color: 'bg-orange-500' }
];

const MODES = [
    { id: 'all', label: 'All Questions', description: 'Include all questions' },
    { id: 'unused', label: 'Unused Only', description: 'Exclude previously answered' },
    { id: 'incorrect', label: 'Incorrect Only', description: 'Only questions you got wrong' }
];

const QUICK_COUNTS = [10, 20, 40];

export default function ExamConfig() {
    const navigate = useNavigate();
    const { user, isConfigured } = useAuth();
    const [selectedSubjects, setSelectedSubjects] = useState(new Set(SUBJECTS.map(s => s.id)));
    const [mode, setMode] = useState('all');
    const [questionCount, setQuestionCount] = useState(20);
    const [customCount, setCustomCount] = useState('');
    const [userProgress, setUserProgress] = useState([]);
    const [availableCount, setAvailableCount] = useState(0);

    useEffect(() => {
        fetchUserProgress();
    }, [user]);

    useEffect(() => {
        calculateAvailableQuestions();
    }, [selectedSubjects, mode, userProgress]);

    const fetchUserProgress = async () => {
        if (!isConfigured || !supabase || !user) {
            setUserProgress([]);
            return;
        }

        try {
            const { data, error } = await supabase
                .from('user_progress')
                .select('question_id, correct')
                .eq('user_id', user.id);

            if (error) throw error;
            setUserProgress(data || []);
        } catch (err) {
            console.error('Error fetching progress:', err);
        }
    };

    const calculateAvailableQuestions = () => {
        let filtered = allQuestions.filter(q => selectedSubjects.has(q.section));

        if (mode === 'unused') {
            const answeredIds = new Set(userProgress.map(p => p.question_id));
            filtered = filtered.filter(q => !answeredIds.has(q.id));
        } else if (mode === 'incorrect') {
            const incorrectIds = new Set(
                userProgress.filter(p => !p.correct).map(p => p.question_id)
            );
            filtered = filtered.filter(q => incorrectIds.has(q.id));
        }

        setAvailableCount(filtered.length);
    };

    const toggleSubject = (subjectId) => {
        setSelectedSubjects(prev => {
            const next = new Set(prev);
            if (next.has(subjectId)) {
                next.delete(subjectId);
            } else {
                next.add(subjectId);
            }
            return next;
        });
    };

    const selectAllSubjects = () => {
        setSelectedSubjects(new Set(SUBJECTS.map(s => s.id)));
    };

    const clearAllSubjects = () => {
        setSelectedSubjects(new Set());
    };

    const handleQuickCount = (count) => {
        setQuestionCount(count);
        setCustomCount('');
    };

    const handleCustomCountChange = (e) => {
        const value = e.target.value;
        setCustomCount(value);
        const num = parseInt(value, 10);
        if (!isNaN(num) && num > 0) {
            setQuestionCount(Math.min(num, availableCount));
        }
    };

    const handleStartExam = () => {
        const config = {
            subjects: Array.from(selectedSubjects),
            mode,
            count: Math.min(questionCount, availableCount)
        };

        sessionStorage.setItem('examConfig', JSON.stringify(config));
        navigate('/exam');
    };

    const handleStartPersonalized = () => {
        // Personalized mode: prioritize unused and incorrect questions
        const config = {
            subjects: Array.from(selectedSubjects),
            mode: 'personalized',
            count: 1 // One question at a time
        };

        sessionStorage.setItem('examConfig', JSON.stringify(config));
        navigate('/exam');
    };

    const canStart = selectedSubjects.size > 0 && availableCount > 0;
    const finalCount = Math.min(questionCount, availableCount);

    return (
        <div className="flex-1 overflow-y-auto bg-gray-50">
            <div className="max-w-3xl mx-auto p-6">
                {/* Header */}
                <div className="flex items-center gap-4 mb-8">
                    <button
                        onClick={() => navigate('/')}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <ChevronLeft className="w-5 h-5 text-gray-600" />
                    </button>
                    <div>
                        <h1 className="text-2xl font-bold text-gray-800">Create New Test</h1>
                        <p className="text-gray-500">Configure your exam session</p>
                    </div>
                </div>

                {/* Personalized Study Mode Card */}
                <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-6 mb-6 text-white">
                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center shrink-0">
                            <Sparkles className="w-6 h-6" />
                        </div>
                        <div className="flex-1">
                            <h2 className="text-lg font-bold mb-1">Personalized Study Mode</h2>
                            <p className="text-purple-100 text-sm mb-4">
                                AI-powered question selection. Prioritizes questions you haven't seen or frequently get wrong.
                                One question at a time with endless practice.
                            </p>
                            <button
                                onClick={handleStartPersonalized}
                                disabled={!canStart}
                                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold transition-all ${canStart
                                        ? 'bg-white text-purple-600 hover:bg-purple-50'
                                        : 'bg-white/30 text-white/60 cursor-not-allowed'
                                    }`}
                            >
                                <Zap className="w-4 h-4" />
                                Start Personalized Study
                            </button>
                        </div>
                    </div>
                </div>

                {/* Divider */}
                <div className="flex items-center gap-4 mb-6">
                    <div className="flex-1 h-px bg-gray-200" />
                    <span className="text-sm text-gray-400 font-medium">OR CREATE CUSTOM TEST</span>
                    <div className="flex-1 h-px bg-gray-200" />
                </div>

                {/* Subject Selection */}
                <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 mb-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-gray-800">Select Subjects</h2>
                        <div className="flex gap-2">
                            <button
                                onClick={selectAllSubjects}
                                className="text-sm text-blue-600 hover:underline"
                            >
                                Select All
                            </button>
                            <span className="text-gray-300">|</span>
                            <button
                                onClick={clearAllSubjects}
                                className="text-sm text-gray-500 hover:underline"
                            >
                                Clear
                            </button>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        {SUBJECTS.map(subject => (
                            <button
                                key={subject.id}
                                onClick={() => toggleSubject(subject.id)}
                                className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${selectedSubjects.has(subject.id)
                                        ? 'border-blue-500 bg-blue-50'
                                        : 'border-gray-200 hover:border-gray-300'
                                    }`}
                            >
                                <div className={`w-3 h-3 rounded-full ${subject.color}`} />
                                <span className={`flex-1 text-left font-medium ${selectedSubjects.has(subject.id) ? 'text-blue-700' : 'text-gray-700'
                                    }`}>
                                    {subject.label}
                                </span>
                                {selectedSubjects.has(subject.id) && (
                                    <Check className="w-4 h-4 text-blue-600" />
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Mode Selection */}
                <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 mb-6">
                    <h2 className="text-lg font-semibold text-gray-800 mb-4">Question Mode</h2>
                    <div className="space-y-3">
                        {MODES.map(m => (
                            <button
                                key={m.id}
                                onClick={() => setMode(m.id)}
                                className={`w-full flex items-center gap-4 p-4 rounded-xl border-2 transition-all text-left ${mode === m.id
                                        ? 'border-blue-500 bg-blue-50'
                                        : 'border-gray-200 hover:border-gray-300'
                                    }`}
                            >
                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${mode === m.id ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
                                    }`}>
                                    {mode === m.id && <div className="w-2 h-2 bg-white rounded-full" />}
                                </div>
                                <div>
                                    <p className={`font-medium ${mode === m.id ? 'text-blue-700' : 'text-gray-700'}`}>
                                        {m.label}
                                    </p>
                                    <p className="text-sm text-gray-500">{m.description}</p>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Question Count */}
                <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 mb-6">
                    <h2 className="text-lg font-semibold text-gray-800 mb-4">Number of Questions</h2>

                    {/* Quick select buttons */}
                    <div className="flex items-center gap-3 mb-4">
                        {QUICK_COUNTS.map(count => (
                            <button
                                key={count}
                                onClick={() => handleQuickCount(count)}
                                disabled={count > availableCount}
                                className={`flex-1 py-3 rounded-xl font-semibold transition-all ${questionCount === count && customCount === ''
                                        ? 'bg-blue-600 text-white'
                                        : count > availableCount
                                            ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                    }`}
                            >
                                {count}
                            </button>
                        ))}
                        <button
                            onClick={() => handleQuickCount(availableCount)}
                            disabled={availableCount === 0}
                            className={`flex-1 py-3 rounded-xl font-semibold transition-all ${questionCount === availableCount && customCount === ''
                                    ? 'bg-blue-600 text-white'
                                    : availableCount === 0
                                        ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
                                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            All ({availableCount})
                        </button>
                    </div>

                    {/* Custom input */}
                    <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-500">Or enter custom:</span>
                        <input
                            type="number"
                            min="1"
                            max={availableCount}
                            value={customCount}
                            onChange={handleCustomCountChange}
                            placeholder="Enter number"
                            className="flex-1 px-4 py-2.5 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none transition-colors text-center font-medium"
                        />
                    </div>

                    <p className="text-center text-sm text-gray-500 mt-3">
                        {availableCount} questions available with current filters
                    </p>
                </div>

                {/* Start Button */}
                <button
                    onClick={handleStartExam}
                    disabled={!canStart || finalCount === 0}
                    className={`w-full flex items-center justify-center gap-3 py-4 rounded-xl font-semibold text-lg transition-all ${canStart && finalCount > 0
                            ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-500/25'
                            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                        }`}
                >
                    <Play className="w-5 h-5" />
                    Start Custom Test ({finalCount} questions)
                </button>
            </div>
        </div>
    );
}
