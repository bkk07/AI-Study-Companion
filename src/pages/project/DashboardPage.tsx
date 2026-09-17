import React from 'react';
import { Brain, AlertTriangle, TrendingUp, Flame, ChevronRight, Info } from 'lucide-react';
import { TOPICS } from '../../data/mockData';
import { SectionHeader, MasteryBar, StatCard, Button } from '../../components/ui';
import { useApp } from '../../context/AppContext';
import type { MasteryLevel } from '../../types';

function getMasteryLevel(v: number): MasteryLevel {
  if (v >= 80) return 'mastered';
  if (v >= 55) return 'developing';
  return 'weak';
}

const TOPIC_MASTERY_DATA = [
  { topic: 'Linear Regression', mcq: 94, applied: 88 },
  { topic: 'Decision Trees', mcq: 91, applied: 84 },
  { topic: 'Classification', mcq: 82, applied: 72 },
  { topic: 'Gradient Descent', mcq: 76, applied: 59 },
  { topic: 'Ridge Regression', mcq: 71, applied: 58 },
  { topic: 'Regularization', mcq: 60, applied: 45 },
  { topic: 'Lasso Regression', mcq: 48, applied: 32 },
];

const FLAGGED_MISMATCHES = [
  { concept: 'Lasso Regression', confidence: 'high', correctness: 48, attempts: 5, insight: 'Your confidence is high but correctness is low. Your mental model may have a gap.' },
  { concept: 'Logistic Regression', confidence: 'high', correctness: 51, attempts: 8, insight: 'High confidence paired with lower applied mastery suggests you recognize but cannot apply this concept.' },
];

const RECOMMENDATIONS = [
  {
    priority: true,
    concept: 'Logistic Regression',
    action: 'Practice',
    reason: 'Your applied mastery (51%) is the lowest among recently practiced topics.',
    view: 'quiz',
  },
  {
    priority: false,
    concept: 'Gradient Descent',
    action: 'Review flashcards',
    reason: '3 flashcards are overdue based on spaced repetition schedule.',
    view: 'flashcards',
  },
  {
    priority: false,
    concept: 'Regularization',
    action: 'Explain it back',
    reason: 'Not yet assessed. Understanding this concept requires applying it — not just recognizing it.',
    view: 'assessments',
  },
  {
    priority: false,
    concept: '8 due flashcards',
    action: 'Review',
    reason: 'Cards are due across Classification and Optimization topics.',
    view: 'flashcards',
  },
];

export default function DashboardPage() {
  const { navigate } = useApp();
  const allC = TOPICS.flatMap(t => t.subtopics.flatMap(s => s.concepts));

  return (
    <div className="max-w-5xl mx-auto px-8 py-10 space-y-10">
      <SectionHeader title="Dashboard" subtitle="Your learning health at a glance" />

      {/* Health cards */}
      <div>
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Your Learning Health</div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <StatCard label="Concepts Mastered" value={allC.filter(c => c.mastery === 'mastered').length} accent="green" icon={<Brain size={18} />} />
          <StatCard label="Developing" value={allC.filter(c => c.mastery === 'developing').length} accent="amber" icon={<TrendingUp size={18} />} />
          <StatCard label="Weak" value={allC.filter(c => c.mastery === 'weak').length} accent="red" icon={<AlertTriangle size={18} />} />
          <StatCard label="Mismatches" value={FLAGGED_MISMATCHES.length} accent="amber" icon={<Info size={18} />} />
          <StatCard label="Study Streak" value="4 days" accent="indigo" icon={<Flame size={18} />} />
        </div>
      </div>

      {/* Mastery overview */}
      <div className="grid sm:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <div className="text-sm font-semibold text-slate-700 mb-4">MCQ Mastery by Topic</div>
          <div className="space-y-3.5">
            {TOPIC_MASTERY_DATA.map(t => (
              <MasteryBar key={t.topic} value={t.mcq} level={getMasteryLevel(t.mcq)} label={t.topic} />
            ))}
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <div className="text-sm font-semibold text-slate-700 mb-4">Applied Mastery by Topic</div>
          <div className="space-y-3.5">
            {TOPIC_MASTERY_DATA.map(t => (
              <MasteryBar key={t.topic} value={t.applied} level={getMasteryLevel(t.applied)} label={t.topic} />
            ))}
          </div>
        </div>
      </div>

      {/* Flagged mismatches */}
      <div>
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Concepts That Need Attention</div>
        <div className="space-y-3">
          {FLAGGED_MISMATCHES.map((m, i) => (
            <div key={i} className="bg-white border border-amber-100 rounded-xl p-5">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 bg-amber-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <AlertTriangle size={16} className="text-amber-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-sm font-semibold text-slate-800">{m.concept}</span>
                    <span className="text-xs text-slate-400">·</span>
                    <span className="text-xs text-red-600 font-medium">{m.correctness}% correct</span>
                    <span className="text-xs text-slate-400">·</span>
                    <span className="text-xs text-amber-600 font-medium">{m.confidence} confidence</span>
                  </div>
                  <p className="text-xs text-slate-500 mb-2">{m.insight}</p>
                  <div className="text-xs text-slate-400">Last {m.attempts} attempts · High confidence, low correctness</div>
                </div>
                <button
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-lg hover:bg-indigo-100 transition-colors flex-shrink-0"
                  onClick={() => navigate('quiz')}
                >
                  Study this
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Decision Trees underconfidence */}
      <div className="bg-white border border-blue-100 rounded-xl p-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-slate-800">Decision Trees</span>
              <span className="text-xs text-green-600 font-medium">82% correct</span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-blue-600 font-medium">Low confidence</span>
            </div>
            <p className="text-xs text-slate-500">You may understand this concept better than you think. Practice to calibrate your confidence.</p>
          </div>
          <button className="text-xs text-indigo-600 hover:underline flex-shrink-0 ml-4">Study <ChevronRight size={12} className="inline" /></button>
        </div>
      </div>

      {/* Recommendations */}
      <div>
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Recommended Next</div>
        {/* Primary */}
        <div className="bg-indigo-600 rounded-xl p-6 text-white mb-4">
          <div className="text-xs text-indigo-300 font-semibold uppercase tracking-wider mb-2">Primary Recommendation</div>
          <h3 className="text-lg font-semibold mb-1">{RECOMMENDATIONS[0].action} {RECOMMENDATIONS[0].concept}</h3>
          <p className="text-indigo-200 text-sm mb-4">{RECOMMENDATIONS[0].reason}</p>
          <button
            className="bg-white text-indigo-700 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-50 transition-colors"
            onClick={() => navigate('quiz')}
          >
            Study this
          </button>
        </div>
        {/* Secondary */}
        <div className="grid sm:grid-cols-3 gap-3">
          {RECOMMENDATIONS.slice(1).map((r, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition-colors">
              <div className="text-xs text-slate-500 mb-0.5">{r.action}</div>
              <div className="text-sm font-semibold text-slate-800 mb-2">{r.concept}</div>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">{r.reason}</p>
              <button
                className="text-xs text-indigo-600 font-medium hover:underline"
                onClick={() => navigate(r.view as any)}
              >
                Go →
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
