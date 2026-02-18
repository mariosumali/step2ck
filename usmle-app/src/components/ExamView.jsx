import QuestionPanel from './QuestionPanel';
import AnswerPanel from './AnswerPanel';
import ExplanationPanel from './ExplanationPanel';
import { useExam } from '../context/ExamContext';

export default function ExamView() {
    const { isSubmitted } = useExam();

    return (
        <div className="flex-1 flex overflow-hidden">
            {/* Left Panel - Question Stem */}
            <div className="w-1/2 border-r border-gray-200 flex flex-col overflow-hidden">
                <QuestionPanel />
            </div>

            {/* Right Panel - Choices and Explanation */}
            <div className="w-1/2 flex flex-col overflow-hidden">
                <AnswerPanel />
                {isSubmitted && <ExplanationPanel />}
            </div>
        </div>
    );
}
