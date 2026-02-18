import { createContext, useContext, useState, useEffect } from 'react';
import { supabase, isSupabaseConfigured } from '../lib/supabase';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [session, setSession] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isSupabaseConfigured()) {
            // Demo mode - no authentication
            setLoading(false);
            return;
        }

        // Check for OAuth callback hash in URL (this handles the redirect from Google)
        const handleOAuthCallback = async () => {
            // If we have a hash with access_token, Supabase will handle it automatically
            const hashParams = new URLSearchParams(window.location.hash.substring(1));
            if (hashParams.get('access_token')) {
                // Let Supabase handle the token exchange
                const { data, error } = await supabase.auth.getSession();
                if (data?.session) {
                    setSession(data.session);
                    setUser(data.session.user);
                    // Clean up the URL hash
                    window.history.replaceState(null, '', window.location.pathname);
                }
                setLoading(false);
                return true;
            }
            return false;
        };

        const initAuth = async () => {
            // First check for OAuth callback
            const wasCallback = await handleOAuthCallback();
            if (wasCallback) return;

            // Get initial session
            const { data: { session } } = await supabase.auth.getSession();
            setSession(session);
            setUser(session?.user ?? null);
            setLoading(false);
        };

        initAuth();

        // Listen for auth changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            async (event, session) => {
                console.log('Auth state changed:', event, session?.user?.email);
                setSession(session);
                setUser(session?.user ?? null);
                setLoading(false);

                // Create profile on first sign in
                if (event === 'SIGNED_IN' && session?.user) {
                    await ensureProfile(session.user);
                }
            }
        );

        return () => subscription.unsubscribe();
    }, []);

    const ensureProfile = async (user) => {
        if (!supabase) return;

        try {
            const { data: existing } = await supabase
                .from('profiles')
                .select('id')
                .eq('id', user.id)
                .single();

            if (!existing) {
                await supabase.from('profiles').insert({
                    id: user.id,
                    email: user.email,
                    avatar_url: user.user_metadata?.avatar_url,
                    display_name: user.user_metadata?.full_name || user.email?.split('@')[0]
                });
            }
        } catch (err) {
            // Profile might already exist or table not set up yet
            console.warn('Profile creation skipped:', err.message);
        }
    };

    const signInWithGoogle = async () => {
        if (!supabase) {
            console.warn('Supabase not configured');
            return { error: { message: 'Supabase not configured' } };
        }

        return supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: `${window.location.origin}/`
            }
        });
    };

    const signOut = async () => {
        if (!supabase) return;
        await supabase.auth.signOut();
        setUser(null);
        setSession(null);
    };

    const value = {
        user,
        session,
        loading,
        isAuthenticated: !!session,
        isConfigured: isSupabaseConfigured(),
        signInWithGoogle,
        signOut
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
