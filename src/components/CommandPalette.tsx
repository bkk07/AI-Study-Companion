import React, { useState, useEffect, useRef } from 'react';
import { Search, MessageCircle, HelpCircle, CreditCard, Map, Upload, BarChart2, X } from 'lucide-react';
import { useApp } from '../context/AppContext';
import type { View } from '../types';

const ACTIONS: { label: string; sub: string; icon: React.ReactNode; view: View }[] = [
  { label: 'Ask Tutor', sub: 'Open AI tutor conversation', icon: <MessageCircle size={16} />, view: 'tutor' },
  { label: 'Start Quiz', sub: 'Begin an adaptive quiz session', icon: <HelpCircle size={16} />, view: 'quiz' },
  { label: 'Review Flashcards', sub: 'Start flashcard review session', icon: <CreditCard size={16} />, view: 'flashcards' },
  { label: 'View Knowledge Map', sub: 'Explore learning structure', icon: <Map size={16} />, view: 'structure' },
  { label: 'Upload Document', sub: 'Add study material to project', icon: <Upload size={16} />, view: 'documents' },
  { label: 'View Dashboard', sub: 'Learning health and progress', icon: <BarChart2 size={16} />, view: 'dashboard' },
];

export default function CommandPalette() {
  const { navigate, setCommandOpen } = useApp();
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setCommandOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const filtered = ACTIONS.filter(
    a =>
      !query ||
      a.label.toLowerCase().includes(query.toLowerCase()) ||
      a.sub.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div
      className="fixed inset-0 bg-slate-900/40 z-50 flex items-start justify-center pt-24"
      onClick={() => setCommandOpen(false)}
    >
      <div
        className="w-full max-w-lg bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100">
          <Search size={16} className="text-slate-400 flex-shrink-0" />
          <input
            ref={inputRef}
            className="flex-1 text-sm text-slate-800 outline-none placeholder:text-slate-400"
            placeholder="Search concepts, documents, or run a command..."
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          <button onClick={() => setCommandOpen(false)}>
            <X size={16} className="text-slate-400 hover:text-slate-600" />
          </button>
        </div>
        <div className="py-2 max-h-80 overflow-y-auto">
          <div className="px-3 pb-1">
            <div className="text-xs text-slate-400 px-1 py-1 uppercase tracking-wide font-medium">Quick actions</div>
            {filtered.map(action => (
              <button
                key={action.label}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-indigo-50 text-left group transition-colors"
                onClick={() => {
                  navigate(action.view);
                  setCommandOpen(false);
                }}
              >
                <span className="text-slate-400 group-hover:text-indigo-600 transition-colors">{action.icon}</span>
                <div>
                  <div className="text-sm font-medium text-slate-800">{action.label}</div>
                  <div className="text-xs text-slate-400">{action.sub}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
        <div className="px-4 py-2.5 border-t border-slate-100 flex items-center gap-3 text-xs text-slate-400">
          <span><kbd className="font-mono-data">↑↓</kbd> navigate</span>
          <span><kbd className="font-mono-data">↵</kbd> select</span>
          <span><kbd className="font-mono-data">Esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
