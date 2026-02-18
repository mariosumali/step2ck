import { useState } from 'react';
import { useExam } from '../context/ExamContext';
import { cleanExplanation } from '../utils/cleanExplanation';
import { CheckCircle2, XCircle, ChevronRight } from 'lucide-react';

export default function ExplanationPanel() {
    const { currentQuestion, isSubmitted, selectedAnswer, nextQuestion, currentQuestionIndex, questions } = useExam();
    const [activeTab, setActiveTab] = useState('correct');

    if (!isSubmitted || !currentQuestion) {
        return null;
    }

    const isCorrect = selectedAnswer === currentQuestion.correctAnswer;
    const cleanedCorrectExplanation = cleanExplanation(currentQuestion.correctExplanation);
    const cleanedIncorrectExplanation = cleanExplanation(currentQuestion.incorrectExplanation);

    return (
        <div className="border-t-2 border-gray-200 bg-white">
            {/* Result banner */}
            <div className={`px-6 py-4 flex items-center gap-3 ${isCorrect ? 'bg-green-50' : 'bg-red-50'
                }`}>
                {isCorrect ? (
                    <>
                        <CheckCircle2 className="w-6 h-6 text-green-500" />
                        <div>
                            <p className="font-semibold text-green-700">Correct!</p>
                            <p className="text-sm text-green-600">
                                You selected {selectedAnswer}. The correct answer is {currentQuestion.correctAnswer}.
                            </p>
                        </div>
                    </>
                ) : (
                    <>
                        <XCircle className="w-6 h-6 text-red-500" />
                        <div>
                            <p className="font-semibold text-red-700">Incorrect</p>
                            <p className="text-sm text-red-600">
                                You selected {selectedAnswer}. The correct answer is {currentQuestion.correctAnswer}.
                            </p>
                        </div>
                    </>
                )}

                {currentQuestionIndex < questions.length - 1 && (
                    <button
                        onClick={nextQuestion}
                        className="ml-auto flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
                    >
                        Next Question
                        <ChevronRight className="w-4 h-4" />
                    </button>
                )}
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200">
                <div className="flex">
                    <button
                        onClick={() => setActiveTab('correct')}
                        className={`px-6 py-3 text-sm font-medium transition-colors ${activeTab === 'correct'
                                ? 'text-blue-600 border-b-2 border-blue-600'
                                : 'text-gray-500 hover:text-gray-700'
                            }`}
                    >
                        Why Correct
                    </button>
                    <button
                        onClick={() => setActiveTab('incorrect')}
                        className={`px-6 py-3 text-sm font-medium transition-colors ${activeTab === 'incorrect'
                                ? 'text-blue-600 border-b-2 border-blue-600'
                                : 'text-gray-500 hover:text-gray-700'
                            }`}
                    >
                        Why Other Choices Are Wrong
                    </button>
                </div>
            </div>

            {/* Explanation content */}
            <div className="p-6 max-h-80 overflow-y-auto custom-scrollbar">
                {activeTab === 'correct' ? (
                    <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed">
                        {cleanedCorrectExplanation || (
                            <p className="text-gray-400 italic">No explanation available for this answer.</p>
                        )}
                    </div>
                ) : (
                    <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed">
                        {cleanedIncorrectExplanation || (
                            <p className="text-gray-400 italic">No explanation available for incorrect choices.</p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
