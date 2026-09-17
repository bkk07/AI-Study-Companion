import React from 'react';
import { FileText, Brain, HelpCircle, CreditCard, BarChart2, Play, MessageCircle, Pen, BookOpen, ChevronRight, AlertTriangle, TrendingUp } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { PROJECTS, TOPICS } from '../../data/mockData';
import { StatCard, MasteryBadge } from '../../components/ui';
import type { MasteryLevel } from '../../types';

function getMasteryLevel(v: number | null): MasteryLevel {
  if (v === null) return 'unassessed';
  if (v >= 80) return 'mastered';
  if (v >= 55) return 'developing';
  return 'weak';
}

export default function OverviewPage() {
  const { navigate, state } = useApp();
  const project = PROJECTS.find(p => p.id === state.selectedProjectId);
  if (!project) return null;

  const allConcepts = TOPICS.flatMap(t => t.subtopics.flatMap(s => s.concepts));
  const mastered = allConcepts.filter(c => c.mastery === 'mastered').length;
  const developing = allConcepts.filter(c => c.mastery === 'developing').length;
  const weak = allConcepts.filter(c => c.mastery === 'weak').length;
  const mismatches = allConcepts.filter(c => c.confidence === 'high' && (c.mcqMastery ?? 100) < 60).length;

  const recommendations = [
    {
      title: 'Strengthen Logistic Regression',
      type: 'quiz',
      reason: 'Your applied mastery (51%) is significantly below your MCQ mastery (78%). This indicates you can recognize but not apply the concept.',
      icon: <HelpCircle size={16} className="text-amber-600" />,
      bg: 'bg-amber-50 border-amber-100',
    },
    {
      title: 'Review Gradient Descent flashcards',
      type: 'flashcard',
      reason: '3 flashcards are due for review today based on spaced repetition schedule.',
      icon: <CreditCard size={16} className="text-indigo-600" />,
      bg: 'bg-indigo-50 border-indigo-100',
    },
    {
      title: 'Explain Regularization in your own words',
      type: 'assessment',
      reason: 'Regularization has not been assessed yet. Explaining it tests deeper understanding than multiple choice.',
      icon: <Pen size={16} className="text-slate-600" />,
      bg: 'bg-slate-50 border-slate-200',
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-8 py-10 space-y-10">
      {/* Header */}
      <div>
        <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Computer Science / {project.name}</div>
        <h1 className="text-2xl font-semibold text-slate-900 font-display">{project.name}</h1>
        <p className="text-slate-500 text-sm mt-0.5">Your personal learning workspace</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard label="Documents" value={project.documentCount} icon={<FileText size={18} />} accent="slate" />
        <StatCard label="Concepts" value={project.conceptCount} icon={<Brain size={18} />} accent="indigo" />
        <StatCard label="Quiz Attempts" value={42} icon={<HelpCircle size={18} />} accent="slate" />
        <StatCard label="Flashcards Reviewed" value={118} icon={<CreditCard size={18} />} accent="slate" />
        <StatCard label="Avg Mastery" value="67%" icon={<BarChart2 size={18} />} accent="green" sub="MCQ + Applied" />
      </div>

      {/* Concept health */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Mastered', value: mastered, color: 'text-green-700', bg: 'bg-green-50 border-green-100' },
          { label: 'Developing', value: developing, color: 'text-amber-700', bg: 'bg-amber-50 border-amber-100' },
          { label: 'Weak', value: weak, color: 'text-red-700', bg: 'bg-red-50 border-red-100' },
          { label: 'Mismatches', value: mismatches, color: 'text-orange-700', bg: 'bg-orange-50 border-orange-100' },
        ].map(item => (
          <div key={item.label} className={`border rounded-lg px-4 py-3 ${item.bg}`}>
            <div className={`text-2xl font-bold font-mono-data ${item.color}`}>{item.value}</div>
            <div className="text-xs text-slate-500 mt-0.5">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Continue Learning */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-start justify-between mb-5">
          <div>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Continue Learning</div>
            <h2 className="text-xl font-semibold text-slate-900">Logistic Regression</h2>
            <div className="flex items-center gap-3 mt-2">
              <MasteryBadge level="developing" />
              <span className="text-xs text-slate-400">Last practiced 25 minutes ago</span>
            </div>
          </div>
          <div className="hidden sm:flex flex-col gap-1 text-right text-xs">
            <span className="font-mono-data text-green-600">MCQ 78%</span>
            <span className="font-mono-data text-amber-600">Applied 51%</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="flex items-center gap-2 bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors" onClick={() => navigate('tutor')}>
            <Play size={14} />
            Continue
          </button>
          <button className="flex items-center gap-2 border border-slate-200 text-slate-700 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-50 transition-colors" onClick={() => navigate('tutor')}>
            <MessageCircle size={14} />
            Ask Tutor
          </button>
          <button className="flex items-center gap-2 border border-slate-200 text-slate-700 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-50 transition-colors" onClick={() => navigate('quiz')}>
            <HelpCircle size={14} />
            Practice
          </button>
          <button className="flex items-center gap-2 border border-slate-200 text-slate-700 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-50 transition-colors" onClick={() => navigate('flashcards')}>
            <CreditCard size={14} />
            Flashcards
          </button>
        </div>
      </div>

      {/* Learning Map mini */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Your Learning Map</div>
            <h2 className="text-base font-semibold text-slate-900">Topics → Subtopics → Concepts</h2>
          </div>
          <button className="text-sm text-indigo-600 hover:underline flex items-center gap-1" onClick={() => navigate('structure')}>
            View full map <ChevronRight size={14} />
          </button>
        </div>
        <div className="space-y-3">
          {TOPICS.map(topic => {
            const allC = topic.subtopics.flatMap(s => s.concepts);
            const masteredC = allC.filter(c => c.mastery === 'mastered').length;
            const topicLevel = getMasteryLevel(masteredC / allC.length >= 0.7 ? 80 : masteredC / allC.length >= 0.4 ? 65 : null);
            return (
              <div key={topic.id} className="flex items-center gap-4 py-2 border-b border-slate-50 last:border-0">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  topicLevel === 'mastered' ? 'bg-green-500' : topicLevel === 'developing' ? 'bg-amber-400' : 'bg-slate-300'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-800">{topic.name}</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {topic.subtopics.length} subtopics · {allC.length} concepts
                  </div>
                </div>
                <div className="text-xs font-mono-data text-slate-500">{masteredC}/{allC.length} mastered</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Today's Plan */}
      <div>
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Today's Recommended Plan</div>
        <div className="space-y-3">
          {recommendations.map((r, i) => (
            <div key={i} className={`border rounded-xl p-5 ${r.bg}`}>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center flex-shrink-0 shadow-sm">
                  {r.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-slate-800">{r.title}</div>
                  <div className="flex items-start gap-1 mt-2">
                    <span className="text-xs font-medium text-slate-500 flex-shrink-0">Why?</span>
                    <p className="text-xs text-slate-500 leading-relaxed">{r.reason}</p>
                  </div>
                </div>
                <button
                  className="text-xs font-medium text-indigo-600 hover:underline flex-shrink-0"
                  onClick={() => navigate(r.type === 'quiz' ? 'quiz' : r.type === 'flashcard' ? 'flashcards' : 'assessments')}
                >
                  Study
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
