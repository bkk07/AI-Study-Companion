import React, { useState } from 'react';
import { BookOpen, Brain, Network, ArrowRight, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';
import { useApp } from '../../context/AppContext';

function KnowledgeGraphSVG() {
  return (
    <svg viewBox="0 0 400 400" className="w-full max-w-sm opacity-80" fill="none">
      {/* Connections */}
      <line x1="200" y1="200" x2="120" y2="120" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="300" y2="130" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="100" y2="280" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="310" y2="290" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="200" y2="320" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="60" y2="190" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="340" y2="200" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="120" y1="120" x2="60" y2="80" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="120" y1="120" x2="190" y2="60" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="300" y1="130" x2="360" y2="80" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="300" y1="130" x2="350" y2="160" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="100" y1="280" x2="50" y2="320" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="310" y1="290" x2="360" y2="340" stroke="#c7d2fe" strokeWidth="1" />
      {/* Leaf nodes */}
      {[
        [60, 80], [190, 60], [360, 80], [350, 160], [50, 320],
        [360, 340], [200, 360], [35, 190], [365, 200],
      ].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="5" fill="#e0e7ff" stroke="#818cf8" strokeWidth="1" />
      ))}
      {/* Mid nodes */}
      {[
        [120, 120], [300, 130], [100, 280], [310, 290], [60, 190], [340, 200], [200, 320],
      ].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="9" fill="#c7d2fe" stroke="#6366f1" strokeWidth="1.5" />
      ))}
      {/* Center node */}
      <circle cx="200" cy="200" r="18" fill="#4f46e5" stroke="#3730a3" strokeWidth="2" />
      <circle cx="200" cy="200" r="10" fill="white" opacity="0.3" />
    </svg>
  );
}

export function LoginPage() {
  const { navigate, state } = useApp();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Use state.isAuthenticated from context — handled in App
  const { navigate: nav } = useApp();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email || !password) { setError('Please enter your email and password.'); return; }
    setLoading(true);
    await new Promise(r => setTimeout(r, 1200));
    setLoading(false);
    if (password === 'wrong') { setError('Invalid credentials. Please try again.'); return; }
    // Simulate successful login
    window.location.href = '/?authenticated=true'; // trigger re-mount
    // Instead just call parent login
    nav('spaces');
    // We need to set isAuthenticated — handle via App.tsx
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col w-1/2 bg-indigo-950 text-white p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-900 to-slate-900" />
        <div className="relative z-10 flex flex-col h-full">
          <div className="flex items-center gap-3 mb-auto">
            <div className="w-9 h-9 rounded-xl bg-indigo-500 flex items-center justify-center">
              <BookOpen size={18} />
            </div>
            <span className="font-semibold text-lg">Study Companion</span>
          </div>
          <div className="flex flex-col items-center justify-center flex-1 gap-10">
            <KnowledgeGraphSVG />
            <div className="text-center max-w-xs">
              <h1 className="font-display text-3xl font-semibold mb-3 leading-snug">
                Turn your own study material into a measurable learning system.
              </h1>
              <p className="text-indigo-300 text-sm leading-relaxed">
                Upload → Understand → Learn → Practice → Explain → Measure → Detect Weakness → Recommend → Improve
              </p>
            </div>
          </div>
          <div className="flex gap-8 mt-auto text-sm text-indigo-400">
            <div className="flex items-center gap-2"><Brain size={14} /> AI-grounded learning</div>
            <div className="flex items-center gap-2"><Network size={14} /> Evidence-based mastery</div>
          </div>
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-slate-900 mb-1">Welcome back</h2>
            <p className="text-slate-500 text-sm">Sign in to continue learning</p>
          </div>

          {error && (
            <div className="mb-4 flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
              <AlertCircle size={15} className="flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1.5">Email address</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@university.edu"
                className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-800 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 placeholder:text-slate-400 transition"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium text-slate-700">Password</label>
                <button type="button" className="text-xs text-indigo-600 hover:underline">Forgot password?</button>
              </div>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-800 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 placeholder:text-slate-400 transition pr-10"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  onClick={() => setShowPw(p => !p)}
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-60 transition flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : null}
              {loading ? 'Signing in…' : 'Sign in'}
              {!loading && <ArrowRight size={15} />}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Don't have an account?{' '}
            <button className="text-indigo-600 font-medium hover:underline" onClick={() => navigate('register')}>
              Create one
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export function RegisterPage() {
  const { navigate } = useApp();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await new Promise(r => setTimeout(r, 1000));
    setLoading(false);
    navigate('spaces');
  };

  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex flex-col w-1/2 bg-indigo-950 text-white p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-900 to-slate-900" />
        <div className="relative z-10 flex flex-col h-full">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500 flex items-center justify-center">
              <BookOpen size={18} />
            </div>
            <span className="font-semibold text-lg">Study Companion</span>
          </div>
          <div className="flex flex-col justify-center flex-1 max-w-xs mx-auto">
            <h1 className="font-display text-3xl font-semibold mb-4 leading-snug">
              A personal AI learning operating system.
            </h1>
            <ul className="space-y-3 text-indigo-300 text-sm">
              {[
                'Upload your own study material',
                'AI-generated knowledge maps from your notes',
                'Evidence-based mastery tracking',
                'Detects confidence vs. correctness mismatches',
                'Personalized study recommendations',
              ].map((s, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full flex-shrink-0" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-slate-900 mb-1">Create your account</h2>
            <p className="text-slate-500 text-sm">Start building your personal learning system</p>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            {[
              { label: 'Full name', key: 'name', type: 'text', placeholder: 'Arjun Reddy' },
              { label: 'Email address', key: 'email', type: 'email', placeholder: 'you@university.edu' },
              { label: 'Password', key: 'password', type: 'password', placeholder: '••••••••' },
              { label: 'Confirm password', key: 'confirm', type: 'password', placeholder: '••••••••' },
            ].map(field => (
              <div key={field.key}>
                <label className="text-sm font-medium text-slate-700 block mb-1.5">{field.label}</label>
                <input
                  type={field.type}
                  placeholder={field.placeholder}
                  value={(form as any)[field.key]}
                  onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-800 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 placeholder:text-slate-400 transition"
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-60 transition flex items-center justify-center gap-2"
            >
              {loading && <Loader2 size={16} className="animate-spin" />}
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Already have an account?{' '}
            <button className="text-indigo-600 font-medium hover:underline" onClick={() => navigate('login')}>
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
