import { useExam } from '../context/ExamContext';
import { cleanQuestionStem } from '../utils/cleanExplanation';

export default function QuestionPanel() {
    const { currentQuestion } = useExam();

    if (!currentQuestion) {
        return (
            <div className="flex-1 flex items-center justify-center text-gray-500">
                No question selected
            </div>
        );
    }

    const cleanedStem = cleanQuestionStem(currentQuestion.questionStem);

    return (
        <div className="flex-1 bg-white overflow-y-auto custom-scrollbar">
            <div className="p-8 max-w-2xl">
                {/* Question metadata */}
                <div className="flex items-center gap-2 mb-4">
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                        {currentQuestion.section}
                    </span>
                    <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded">
                        {currentQuestion.subsection}
                    </span>
                    {currentQuestion.system !== 'Unknown' && (
                        <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded">
                            {currentQuestion.system}
                        </span>
                    )}
                </div>

                {/* Question stem */}
                <div className="question-stem text-gray-800 leading-relaxed">
                    {cleanedStem}
                </div>

                {/* Hint for text selection */}
                <p className="mt-6 text-xs text-gray-400 italic">
                    Tip: Select any text to highlight it for reference
                </p>
            </div>
        </div>
    );
}
