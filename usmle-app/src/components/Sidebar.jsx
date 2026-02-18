import { useState } from 'react';
import { ChevronRight, ChevronDown, FileText, FolderOpen, Folder } from 'lucide-react';
import { useExam } from '../context/ExamContext';

// Group questions by section for sidebar display
function getQuestionsBySection(questions) {
    const grouped = {};
    questions.forEach((q, index) => {
        const section = q.section || 'Unknown';
        const subsection = q.subsection || 'General';

        if (!grouped[section]) {
            grouped[section] = {};
        }
        if (!grouped[section][subsection]) {
            grouped[section][subsection] = [];
        }
        grouped[section][subsection].push({ ...q, examIndex: index });
    });
    return grouped;
}

function SubsectionItem({ subsection, questions }) {
    const [isOpen, setIsOpen] = useState(true);
    const { goToQuestion, currentQuestion, getProgress, answeredQuestions } = useExam();

    const progress = getProgress(questions);

    return (
        <div className="ml-4">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 w-full px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
            >
                {isOpen ? (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
                {isOpen ? (
                    <FolderOpen className="w-4 h-4 text-blue-500" />
                ) : (
                    <Folder className="w-4 h-4 text-blue-500" />
                )}
                <span className="flex-1 text-left font-medium">{subsection}</span>
                <span className="text-xs text-gray-400">
                    {progress.completed}/{progress.total}
                </span>
            </button>

            {isOpen && (
                <div className="ml-6 mt-1 space-y-0.5">
                    {questions.map((question) => {
                        const isAnswered = answeredQuestions.has(question.id);
                        const answerData = answeredQuestions.get(question.id);

                        return (
                            <button
                                key={question.id}
                                onClick={() => goToQuestion(question.examIndex)}
                                className={`flex items-center gap-2 w-full px-2 py-1.5 text-sm rounded transition-colors ${currentQuestion?.id === question.id
                                        ? 'bg-blue-100 text-blue-700'
                                        : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                            >
                                <FileText className={`w-3.5 h-3.5 ${isAnswered
                                        ? answerData?.correct ? 'text-green-500' : 'text-red-500'
                                        : 'text-gray-400'
                                    }`} />
                                <span>Q{question.examIndex + 1}</span>
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

function SectionItem({ section, subsections }) {
    const [isOpen, setIsOpen] = useState(true);

    return (
        <div className="mb-2">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
                {isOpen ? (
                    <ChevronDown className="w-4 h-4 text-gray-500" />
                ) : (
                    <ChevronRight className="w-4 h-4 text-gray-500" />
                )}
                <span className="flex-1 text-left">{section}</span>
            </button>

            {isOpen && (
                <div className="mt-1">
                    {Object.entries(subsections).map(([subsection, questions]) => (
                        <SubsectionItem
                            key={subsection}
                            subsection={subsection}
                            questions={questions}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

export default function Sidebar() {
    const { questions } = useExam();
    const groupedQuestions = getQuestionsBySection(questions);

    return (
        <aside className="w-64 bg-white border-r border-gray-200 h-full overflow-y-auto custom-scrollbar">
            <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-800">Questions</h2>
                <p className="text-xs text-gray-500 mt-1">{questions.length} questions in this exam</p>
            </div>

            <nav className="p-3">
                {Object.entries(groupedQuestions).map(([section, subsections]) => (
                    <SectionItem
                        key={section}
                        section={section}
                        subsections={subsections}
                    />
                ))}
            </nav>
        </aside>
    );
}
