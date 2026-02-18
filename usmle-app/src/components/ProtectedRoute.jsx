import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// TODO: Re-enable auth checks when done debugging
export default function ProtectedRoute({ children }) {
    // TEMPORARILY DISABLED - bypass all auth
    return children;

    /* ORIGINAL AUTH LOGIC - uncomment to re-enable:
    const { isAuthenticated, loading, isConfigured } = useAuth();

    if (!isConfigured) {
        return children;
    }

    if (loading) {
        return (
            <div className="h-screen flex items-center justify-center bg-gray-100">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-gray-600">Loading...</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return children;
    */
}
