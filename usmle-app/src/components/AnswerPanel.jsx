import { useExam } from '../context/ExamContext';
import { cleanChoiceText } from '../utils/cleanExplanation';
import { CheckCircle2, XCircle, ArrowRight, Sparkles } from 'lucide-react';

function ChoiceCard({ letter, text, isSelected, isStruckThrough, isCorrect, isSubmitted, onSelect, onStrikethrough }) {
    const cleanedText = cleanChoiceText(text);

    const handleClick = (e) => {
        e.preventDefault();
        onSelect();
    };

    const handleContextMenu = (e) => {
        e.preventDefault();
        onStrikethrough();
    };

    // Determine border color based on state
    let borderClass = 'border-gray-200 hover:border-gray-300';
    let bgClass = 'bg-white hover:bg-gray-50';

    if (isSubmitted) {
        if (isCorrect) {
            borderClass = 'border-green-500';
            bgClass = 'bg-green-50';
        } else if (isSelected) {
            borderClass = 'border-red-500';
            bgClass = 'bg-red-50';
        }
    } else if (isSelected) {
        borderClass = 'border-blue-500';
        bgClass = 'bg-blue-50';
    }

    return (
        <button
            onClick={handleClick}
            onContextMenu={handleContextMenu}
            disabled={isSubmitted}
            className={`w-full text-left p-4 rounded-lg border-2 transition-all ${borderClass} ${bgClass} ${isSubmitted ? 'cursor-default' : 'cursor-pointer'
                }`}
        >
            <div className="flex items-start gap-3">
                <span className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${isSubmitted && isCorrect
                    ? 'bg-green-500 text-white'
                    : isSubmitted && isSelected
                        ? 'bg-red-500 text-white'
                        : isSelected
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-200 text-gray-700'
                    }`}>
                    {letter}
                </span>

                <span className={`flex-1 text-gray-700 ${isStruckThrough ? 'strikethrough' : ''}`}>
                    {cleanedText}
                </span>

                {isSubmitted && isCorrect && (
                    <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                )}
                {isSubmitted && isSelected && !isCorrect && (
                    <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                )}
            </div>
        </button>
    );
}

export default function AnswerPanel() {
    const {
        currentQuestion,
        selectedAnswer,
        struckThroughChoices,
        isSubmitted,
        isPersonalizedMode,
        selectAnswer,
        toggleStrikethrough,
        submit,
        nextQuestion,
        questions,
        currentQuestionIndex
    } = useExam();

    if (!currentQuestion) {
        return null;
    }

    const choices = Object.entries(currentQuestion.choices);
    const isLastQuestion = !isPersonalizedMode && currentQuestionIndex >= questions.length - 1;

    return (
        <div className="flex-1 bg-gray-50 flex flex-col overflow-hidden">
            {/* Personalized mode badge */}
            {isPersonalizedMode && (
                <div className="px-6 pt-4">
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-100 text-purple-700 rounded-full w-fit text-sm font-medium">
                        <Sparkles className="w-4 h-4" />
                        Personalized Study
                    </div>
                </div>
            )}

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
                    Select your answer
                </h3>

                <div className="space-y-3">
                    {choices.map(([letter, text]) => (
                        <ChoiceCard
                            key={letter}
                            letter={letter}
                            text={text}
                            isSelected={selectedAnswer === letter}
                            isStruckThrough={struckThroughChoices.has(letter)}
                            isCorrect={letter === currentQuestion.correctAnswer}
                            isSubmitted={isSubmitted}
                            onSelect={() => selectAnswer(letter)}
                            onStrikethrough={() => toggleStrikethrough(letter)}
                        />
                    ))}
                </div>

                {!isSubmitted && (
                    <p className="mt-4 text-xs text-gray-400">
                        Right-click on a choice to strike it through
                    </p>
                )}
            </div>

            {/* Fixed button area */}
            <div className="p-4 border-t border-gray-200 bg-white">
                {!isSubmitted ? (
                    <button
                        onClick={submit}
                        disabled={!selectedAnswer}
                        className={`w-full py-3 px-6 rounded-lg font-semibold text-white transition-all ${selectedAnswer
                            ? 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'
                            : 'bg-gray-300 cursor-not-allowed'
                            }`}
                    >
                        Submit Answer
                    </button>
                ) : (
                    // Show "Next Question" button after submission
                    <button
                        onClick={nextQuestion}
                        disabled={isLastQuestion}
                        className={`w-full flex items-center justify-center gap-2 py-3 px-6 rounded-lg font-semibold transition-all ${isLastQuestion
                                ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                : isPersonalizedMode
                                    ? 'bg-purple-600 hover:bg-purple-700 text-white active:scale-[0.98]'
                                    : 'bg-blue-600 hover:bg-blue-700 text-white active:scale-[0.98]'
                            }`}
                    >
                        {isPersonalizedMode ? (
                            <>
                                <Sparkles className="w-4 h-4" />
                                Next Personalized Question
                            </>
                        ) : isLastQuestion ? (
                            'Exam Complete'
                        ) : (
                            <>
                                Next Question
                                <ArrowRight className="w-4 h-4" />
                            </>
                        )}
                    </button>
                )}
            </div>
        </div>
    );
}
