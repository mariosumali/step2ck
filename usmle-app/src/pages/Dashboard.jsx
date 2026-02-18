import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Plus, TrendingUp, Target, Clock } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../context/AuthContext';

const COLORS = ['#22c55e', '#ef4444'];
const SECTION_COLORS = {
    'Internal Medicine': '#3b82f6',
    'Surgery': '#ef4444',
    'OB/GYN': '#ec4899',
    'Pediatrics': '#f59e0b',
    'Neurology': '#8b5cf6',
    'Psychiatry': '#06b6d4',
    'Family Medicine': '#10b981',
    'Emergency Medicine': '#f97316'
};

export default function Dashboard() {
    const navigate = useNavigate();
    const { user, isConfigured } = useAuth();
    const [stats, setStats] = useState({
        total: 0,
        correct: 0,
        incorrect: 0,
        bySection: []
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
    }, [user]);

    const fetchStats = async () => {
        if (!isConfigured || !supabase || !user) {
            // Demo mode - empty stats
            setStats({
                total: 0,
                correct: 0,
                incorrect: 0,
                bySection: []
            });
            setLoading(false);
            return;
        }

        try {
            // Add timeout to prevent hanging
            const timeoutPromise = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Timeout')), 5000)
            );

            const fetchPromise = supabase
                .from('user_progress')
                .select('*')
                .eq('user_id', user.id);

            const { data, error } = await Promise.race([fetchPromise, timeoutPromise]);

            if (error) throw error;
            if (!data) {
                setLoading(false);
                return;
            }

            const correct = data.filter(d => d.correct).length;
            const incorrect = data.filter(d => !d.correct).length;

            // Group by section
            const sectionMap = {};
            data.forEach(d => {
                if (!sectionMap[d.section]) {
                    sectionMap[d.section] = { correct: 0, total: 0 };
                }
                sectionMap[d.section].total++;
                if (d.correct) sectionMap[d.section].correct++;
            });

            const bySection = Object.entries(sectionMap).map(([name, data]) => ({
                name: name.replace(' Medicine', '').replace('Emergency', 'EM'),
                accuracy: Math.round((data.correct / data.total) * 100),
                total: data.total,
                fill: SECTION_COLORS[name] || '#6b7280'
            }));

            setStats({
                total: data.length,
                correct,
                incorrect,
                bySection
            });
        } catch (err) {
            console.error('Error fetching stats:', err);
            // On error, show empty stats instead of hanging
            setStats({
                total: 0,
                correct: 0,
                incorrect: 0,
                bySection: []
            });
        } finally {
            setLoading(false);
        }
    };

    const accuracy = stats.total > 0
        ? Math.round((stats.correct / stats.total) * 100)
        : 0;

    const pieData = stats.total > 0
        ? [
            { name: 'Correct', value: stats.correct },
            { name: 'Incorrect', value: stats.incorrect }
        ]
        : [{ name: 'No data', value: 1 }];

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
                        <p className="text-gray-500">Track your USMLE preparation progress</p>
                    </div>
                    <button
                        onClick={() => navigate('/exam/config')}
                        className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors font-semibold shadow-lg shadow-blue-500/25"
                    >
                        <Plus className="w-5 h-5" />
                        Create New Test
                    </button>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                                <Target className="w-6 h-6 text-blue-600" />
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Questions Answered</p>
                                <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                                <TrendingUp className="w-6 h-6 text-green-600" />
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Overall Accuracy</p>
                                <p className="text-2xl font-bold text-gray-800">{accuracy}%</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center">
                                <Clock className="w-6 h-6 text-amber-600" />
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Correct / Incorrect</p>
                                <p className="text-2xl font-bold text-gray-800">
                                    <span className="text-green-600">{stats.correct}</span>
                                    {' / '}
                                    <span className="text-red-500">{stats.incorrect}</span>
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Accuracy Donut */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-800 mb-4">Accuracy Overview</h2>
                        <div className="h-64 flex items-center justify-center">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={pieData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={60}
                                        outerRadius={90}
                                        paddingAngle={2}
                                        dataKey="value"
                                    >
                                        {pieData.map((entry, index) => (
                                            <Cell
                                                key={`cell-${index}`}
                                                fill={stats.total > 0 ? COLORS[index % COLORS.length] : '#e5e7eb'}
                                            />
                                        ))}
                                    </Pie>
                                    <Tooltip />
                                </PieChart>
                            </ResponsiveContainer>
                            <div className="absolute flex flex-col items-center">
                                <span className="text-3xl font-bold text-gray-800">{accuracy}%</span>
                                <span className="text-sm text-gray-500">Accuracy</span>
                            </div>
                        </div>
                    </div>

                    {/* Performance by Section */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-800 mb-4">Performance by Section</h2>
                        {stats.bySection.length > 0 ? (
                            <div className="h-64">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={stats.bySection} layout="vertical">
                                        <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                                        <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
                                        <Tooltip formatter={(value) => `${value}%`} />
                                        <Bar dataKey="accuracy" radius={[0, 4, 4, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        ) : (
                            <div className="h-64 flex items-center justify-center text-gray-400">
                                <p>No data yet. Start a test to see your performance!</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Quick Start */}
                {stats.total === 0 && (
                    <div className="mt-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-8 text-white">
                        <h2 className="text-xl font-bold mb-2">Ready to start studying?</h2>
                        <p className="text-blue-100 mb-4">
                            Create your first custom test and track your progress towards USMLE success.
                        </p>
                        <button
                            onClick={() => navigate('/exam/config')}
                            className="px-6 py-3 bg-white text-blue-600 rounded-xl font-semibold hover:bg-blue-50 transition-colors"
                        >
                            Create Your First Test
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
