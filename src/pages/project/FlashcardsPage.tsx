import React, { useState } from 'react';
import { Plus, CreditCard, CheckCircle, Clock, Star, Search, Trash2, Edit3, Play, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import { FLASHCARDS } from '../../data/mockData';
import { SectionHeader, EmptyState, Button, Tag } from '../../components/ui';
import type { Flashcard } from '../../types';

type SubView = 'dashboard' | 'study' | 'library' | 'generate';

export default function FlashcardsPage() {
  const [subView, setSubView] = useState<SubView>('dashboard');
  const [studyIndex, setStudyIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [filterState, setFilterState] = useState<string>('all');

  const dueCards = FLASHCARDS.filter(f => f.state !== 'mastered');
  const newCards = FLASHCARDS.filter(f => f.state === 'new');
  const learning = FLASHCARDS.filter(f => f.state === 'learning');
  const mastered = FLASHCARDS.filter(f => f.state === 'mastered');

  if (subView === 'study') {
    return (
      <StudyMode
        cards={dueCards}
        index={studyIndex}
        flipped={flipped}
        setFlipped={setFlipped}
        setIndex={(i) => { setStudyIndex(i); setFlipped(false); }}
        onExit={() => setSubView('dashboard')}
      />
    );
  }

  if (subView === 'generate') {
    return <GenerateView onBack={() => setSubView('dashboard')} />;
  }

  return (
    <div className="max-w-5xl mx-auto px-8 py-10">
      <div className="flex items-center justify-between mb-6">
        <SectionHeader title="Flashcards" subtitle="Spaced repetition review of your concepts" />
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setSubView('library')}>Library</Button>
          <Button variant="secondary" size="sm" onClick={() => setSubView('generate')}>
            <Plus size={14} />Generate
          </Button>
        </div>
      </div>

      {subView === 'dashboard' && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
            {[
              { label: 'Total cards', value: FLASHCARDS.length, color: 'text-slate-800' },
              { label: 'Due today', value: dueCards.length, color: 'text-indigo-600' },
              { label: 'New', value: newCards.length, color: 'text-blue-600' },
              { label: 'Learning', value: learning.length, color: 'text-amber-600' },
              { label: 'Mastered', value: mastered.length, color: 'text-green-600' },
            ].map(s => (
              <div key={s.label} className="bg-white border border-slate-200 rounded-xl px-4 py-4 text-center">
                <div className={`text-2xl font-bold font-mono-data ${s.color}`}>{s.value}</div>
                <div className="text-xs text-slate-500 mt-1">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Continue review */}
          {dueCards.length > 0 ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 flex items-center gap-8">
              <div className="w-16 h-16 bg-indigo-50 border border-indigo-100 rounded-2xl flex items-center justify-center flex-shrink-0">
                <CreditCard size={28} className="text-indigo-600" />
              </div>
              <div className="flex-1">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Continue Review</div>
                <h2 className="text-xl font-semibold text-slate-900">{dueCards.length} cards due</h2>
                <p className="text-sm text-slate-500 mt-1">Complete your spaced repetition review to maintain mastery</p>
              </div>
              <button
                className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-lg font-medium text-sm hover:bg-indigo-700 transition-colors"
                onClick={() => { setStudyIndex(0); setFlipped(false); setSubView('study'); }}
              >
                <Play size={15} />
                Start Review
              </button>
            </div>
          ) : (
            <EmptyState icon={<Star size={22} />} title="All caught up!" description="No cards are due today. Come back tomorrow or generate new cards." />
          )}

          {/* Recent cards preview */}
          <div className="mt-8">
            <div className="text-sm font-semibold text-slate-700 mb-3">Recent flashcards</div>
            <div className="space-y-2">
              {FLASHCARDS.slice(0, 5).map(card => (
                <div key={card.id} className="bg-white border border-slate-200 rounded-lg px-4 py-3 flex items-center gap-4">
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                    card.state === 'mastered' ? 'bg-green-500' : card.state === 'learning' ? 'bg-amber-400' : 'bg-blue-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-700 truncate">{card.front}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{card.concept}</p>
                  </div>
                  <Tag color={card.state === 'mastered' ? 'green' : card.state === 'learning' ? 'amber' : 'indigo'}>
                    {card.state}
                  </Tag>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {subView === 'library' && (
        <LibraryView cards={FLASHCARDS} filter={filterState} setFilter={setFilterState} onStudy={(idx) => { setStudyIndex(idx); setFlipped(false); setSubView('study'); }} />
      )}
    </div>
  );
}

function StudyMode({
  cards, index, flipped, setFlipped, setIndex, onExit,
}: {
  cards: Flashcard[];
  index: number;
  flipped: boolean;
  setFlipped: (v: boolean) => void;
  setIndex: (i: number) => void;
  onExit: () => void;
}) {
  const card = cards[index];
  if (!card) return null;

  const progress = ((index + 1) / cards.length) * 100;

  return (
    <div className="min-h-full flex flex-col items-center justify-center px-8 py-10 bg-slate-50">
      {/* Top bar */}
      <div className="w-full max-w-xl mb-8">
        <div className="flex items-center justify-between mb-3 text-sm text-slate-500">
          <span className="font-medium">Machine Learning</span>
          <span className="font-mono-data">Card {index + 1} / {cards.length}</span>
        </div>
        <div className="h-1 bg-slate-200 rounded-full">
          <div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {/* Card */}
      <div
        className="card-flip-container w-full max-w-xl cursor-pointer"
        style={{ height: 280 }}
        onClick={() => setFlipped(!flipped)}
      >
        <div className={`card-inner ${flipped ? 'flipped' : ''}`}>
          {/* Front */}
          <div className="card-face bg-white border border-slate-200 rounded-2xl flex flex-col items-center justify-center p-10 shadow-sm">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-5">Question</div>
            <p className="text-lg font-medium text-slate-800 text-center leading-relaxed">{card.front}</p>
            <p className="text-xs text-slate-400 mt-6">Click to reveal answer</p>
          </div>
          {/* Back */}
          <div className="card-face card-back-face bg-indigo-50 border border-indigo-100 rounded-2xl flex flex-col items-start justify-start p-8 shadow-sm overflow-y-auto">
            <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-4">Answer</div>
            <p className="text-base text-slate-700 leading-relaxed">{card.back}</p>
            <div className="mt-5 pt-4 border-t border-indigo-100 w-full">
              <p className="text-xs text-slate-400">{card.source}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recall buttons */}
      <div className={`mt-8 transition-opacity ${flipped ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}>
        <p className="text-xs text-slate-500 text-center mb-3 font-medium uppercase tracking-wide">How well did you recall this?</p>
        <div className="flex gap-3">
          {[
            { label: 'Again', color: 'bg-red-50 border-red-200 text-red-600 hover:bg-red-100', next: 1 },
            { label: 'Hard', color: 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100', next: 3 },
            { label: 'Good', color: 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100', next: 4 },
            { label: 'Easy', color: 'bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100', next: 7 },
          ].map(btn => (
            <button
              key={btn.label}
              className={`px-5 py-2.5 rounded-xl border text-sm font-semibold transition-colors ${btn.color}`}
              onClick={() => {
                if (index < cards.length - 1) setIndex(index + 1);
                else onExit();
              }}
            >
              {btn.label}
              <div className="text-xs font-normal opacity-60 mt-0.5">+{btn.next}d</div>
            </button>
          ))}
        </div>
      </div>

      {/* Nav */}
      <div className="flex items-center gap-4 mt-8">
        <button
          className="p-2 rounded-lg border border-slate-200 text-slate-400 hover:text-slate-600 hover:bg-slate-100 disabled:opacity-30 transition-colors"
          disabled={index === 0}
          onClick={() => setIndex(index - 1)}
        >
          <ChevronLeft size={18} />
        </button>
        <button className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors" onClick={() => setFlipped(false)}>
          <RotateCcw size={12} />Reset
        </button>
        <button
          className="p-2 rounded-lg border border-slate-200 text-slate-400 hover:text-slate-600 hover:bg-slate-100 disabled:opacity-30 transition-colors"
          disabled={index === cards.length - 1}
          onClick={() => setIndex(index + 1)}
        >
          <ChevronRight size={18} />
        </button>
        <button className="ml-4 text-xs text-slate-400 hover:text-slate-600 transition-colors" onClick={onExit}>Exit</button>
      </div>
    </div>
  );
}

function LibraryView({ cards, filter, setFilter, onStudy }: {
  cards: Flashcard[];
  filter: string;
  setFilter: (f: string) => void;
  onStudy: (idx: number) => void;
}) {
  const [search, setSearch] = useState('');
  const filters = ['all', 'due', 'new', 'learning', 'mastered'];
  const filtered = cards.filter(c => {
    const matchState = filter === 'all' || filter === 'due' ? (filter === 'due' ? c.state !== 'mastered' : true) : c.state === filter;
    const matchSearch = !search || c.front.toLowerCase().includes(search.toLowerCase()) || c.concept.toLowerCase().includes(search.toLowerCase());
    return matchState && matchSearch;
  });

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 outline-none focus:border-indigo-400 placeholder:text-slate-400"
            placeholder="Search flashcards…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-1">
          {filters.map(f => (
            <button
              key={f}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${filter === f ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:bg-slate-100'}`}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        {filtered.map((card, i) => (
          <div key={card.id} className="bg-white border border-slate-200 rounded-xl px-5 py-4 hover:border-slate-300 transition-colors">
            <div className="flex items-start gap-4">
              <div className="flex-1 min-w-0">
                <div className="text-xs text-slate-400 mb-1">{card.concept}</div>
                <p className="text-sm font-medium text-slate-800 line-clamp-2">{card.front}</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Tag color={card.state === 'mastered' ? 'green' : card.state === 'learning' ? 'amber' : 'indigo'}>{card.state}</Tag>
                <button className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded" onClick={() => onStudy(i)}>
                  <Play size={14} />
                </button>
                <button className="p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
            {card.lastReviewed && (
              <div className="mt-2 flex gap-4 text-xs text-slate-400">
                <span className="flex items-center gap-1"><Clock size={11} />Last: {card.lastReviewed}</span>
                {card.nextReview && <span className="flex items-center gap-1"><ChevronRight size={11} />Next: {card.nextReview}</span>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function GenerateView({ onBack }: { onBack: () => void }) {
  const [scope, setScope] = useState('project');
  const [count, setCount] = useState('10');
  const [difficulty, setDifficulty] = useState('intermediate');
  const [generated, setGenerated] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    await new Promise(r => setTimeout(r, 1500));
    setLoading(false);
    setGenerated(true);
  };

  const preview = [
    { front: 'What distinguishes Ridge from Lasso regression in terms of coefficient behavior?', back: 'Ridge shrinks all coefficients proportionally but rarely to zero. Lasso can shrink coefficients exactly to zero, enabling feature selection.', concept: 'Ridge vs. Lasso', source: 'Regularization Techniques.pdf — p.38' },
    { front: 'Define the role of the learning rate in gradient descent convergence.', back: 'The learning rate η controls the step size in parameter space. Too large: divergence. Too small: slow convergence. Adaptive rates (Adam, RMSprop) adjust η during training.', concept: 'Gradient Descent', source: 'Machine Learning Notes.pdf — p.118' },
    { front: 'What is the purpose of bootstrapping in Random Forests?', back: 'Random sampling with replacement creates diverse training subsets, reducing variance across trees and making the ensemble more robust than any single tree.', concept: 'Random Forests', source: 'Ensemble Methods.pdf — p.20' },
  ];

  return (
    <div className="max-w-2xl">
      <button className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6 transition-colors" onClick={onBack}>
        <ChevronLeft size={16} />Back
      </button>

      {!generated ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 space-y-6">
          <h2 className="text-lg font-semibold text-slate-900">Generate Flashcards</h2>

          <div>
            <label className="text-sm font-medium text-slate-700 block mb-2">Scope</label>
            <div className="flex flex-wrap gap-2">
              {['project', 'topic', 'subtopic', 'concept', 'document'].map(s => (
                <button
                  key={s}
                  className={`px-3 py-1.5 rounded-lg border text-sm capitalize transition-colors ${scope === s ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-slate-200 text-slate-600 hover:border-slate-300'}`}
                  onClick={() => setScope(s)}
                >
                  {s === 'project' ? 'Entire Project' : s}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700 block mb-2">Number of cards</label>
            <div className="flex gap-2">
              {['5', '10', '20', 'Custom'].map(n => (
                <button
                  key={n}
                  className={`px-4 py-1.5 rounded-lg border text-sm transition-colors ${count === n ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-slate-200 text-slate-600 hover:border-slate-300'}`}
                  onClick={() => setCount(n)}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700 block mb-2">Difficulty</label>
            <div className="flex gap-2">
              {['basic', 'intermediate', 'advanced'].map(d => (
                <button
                  key={d}
                  className={`px-4 py-1.5 rounded-lg border text-sm capitalize transition-colors ${difficulty === d ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-slate-200 text-slate-600 hover:border-slate-300'}`}
                  onClick={() => setDifficulty(d)}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          <button
            className="flex items-center gap-2 bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-60 transition-colors"
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
            {loading ? 'Generating…' : 'Generate'}
          </button>
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-900">Preview — {preview.length} cards generated</h2>
            <button className="text-sm bg-indigo-600 text-white px-4 py-1.5 rounded-lg hover:bg-indigo-700 transition-colors">Save all</button>
          </div>
          <div className="space-y-4">
            {preview.map((c, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-xl p-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs font-medium text-slate-400 mb-1.5">Front</div>
                    <p className="text-sm text-slate-700 leading-relaxed">{c.front}</p>
                  </div>
                  <div className="border-l border-slate-100 pl-4">
                    <div className="text-xs font-medium text-slate-400 mb-1.5">Back</div>
                    <p className="text-sm text-slate-600 leading-relaxed">{c.back}</p>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-50 flex items-center justify-between">
                  <div className="text-xs text-slate-400">{c.concept} · {c.source}</div>
                  <div className="flex gap-1">
                    <button className="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"><Edit3 size={13} /></button>
                    <button className="p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded"><Trash2 size={13} /></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
