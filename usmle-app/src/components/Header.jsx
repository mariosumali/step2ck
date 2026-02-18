import { useNavigate, useLocation } from 'react-router-dom';
import { FlaskConical, ChevronLeft, ChevronRight, Home, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Header({ showExamNav = false, examContext = null }) {
    const navigate = useNavigate();
    const location = useLocation();
    const { user, signOut, isConfigured } = useAuth();

    const handleLogout = async () => {
        await signOut();
        navigate('/login');
    };

    const isExamPage = location.pathname === '/exam';

    return (
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
            <div className="flex items-center gap-4">
                <button
                    onClick={() => navigate('/')}
                    className="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                    <Home className="w-5 h-5" />
                    <h1 className="text-lg font-bold text-gray-800">USMLE Prep</h1>
                </button>

                {isExamPage && examContext && (
                    <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                        Question {examContext.currentQuestionIndex + 1} of {examContext.questions.length}
                    </span>
                )}
            </div>

            <div className="flex items-center gap-3">
                {isExamPage && examContext && (
                    <>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={examContext.prevQuestion}
                                disabled={examContext.currentQuestionIndex === 0}
                                className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                                title="Previous question"
                            >
                                <ChevronLeft className="w-5 h-5 text-gray-600" />
                            </button>
                            <button
                                onClick={examContext.nextQuestion}
                                disabled={examContext.currentQuestionIndex === examContext.questions.length - 1}
                                className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                                title="Next question"
                            >
                                <ChevronRight className="w-5 h-5 text-gray-600" />
                            </button>
                        </div>
                        <div className="h-6 w-px bg-gray-200" />
                    </>
                )}

                <button
                    className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors font-medium text-sm"
                    onClick={() => alert('Lab Values - Coming Soon!')}
                >
                    <FlaskConical className="w-4 h-4" />
                    Lab Values
                </button>

                <div className="h-6 w-px bg-gray-200" />

                {/* User Profile / Logout */}
                {isConfigured && user ? (
                    <div className="flex items-center gap-3">
                        <img
                            src={user.user_metadata?.avatar_url || `https://ui-avatars.com/api/?name=${user.email}`}
                            alt="Profile"
                            className="w-8 h-8 rounded-full border-2 border-gray-200"
                        />
                        <button
                            onClick={handleLogout}
                            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                            title="Sign out"
                        >
                            <LogOut className="w-5 h-5" />
                        </button>
                    </div>
                ) : (
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">Demo Mode</span>
                )}
            </div>
        </header>
    );
}
