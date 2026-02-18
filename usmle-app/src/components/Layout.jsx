import { useLocation } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import { useExam } from '../context/ExamContext';

export default function Layout({ children, showSidebar = false }) {
    const location = useLocation();
    const isExamPage = location.pathname === '/exam';

    // Only try to use exam context on exam page
    let examContext = null;
    if (isExamPage) {
        try {
            examContext = useExam();
        } catch (e) {
            // Not in exam context
        }
    }

    return (
        <div className="h-screen flex flex-col bg-gray-100">
            <Header showExamNav={isExamPage} examContext={examContext} />
            <div className="flex-1 flex overflow-hidden">
                {showSidebar && isExamPage && <Sidebar />}
                {children}
            </div>
        </div>
    );
}
