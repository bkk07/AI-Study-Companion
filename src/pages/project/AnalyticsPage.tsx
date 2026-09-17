import React, { useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell, ReferenceLine
} from 'recharts';
import { SectionHeader, StatCard } from '../../components/ui';
import { MASTERY_OVER_TIME, TOPIC_MASTERY } from '../../data/mockData';
import { FileText, Brain, HelpCircle, CreditCard, MessageCircle, ClipboardCheck } from 'lucide-react';

const CONFIDENCE_CORRECTNESS = [
  { concept: 'Linear Regression', confidence: 90, correctness: 94, name: 'LR' },
  { concept: 'Decision Trees', confidence: 40, correctness: 91, name: 'DT' },
  { concept: 'Logistic Regression', confidence: 85, correctness: 65, name: 'LogR' },
  { concept: 'Gradient Descent', confidence: 65, correctness: 76, name: 'GD' },
  { concept: 'Ridge Regression', confidence: 60, correctness: 71, name: 'RR' },
  { concept: 'Lasso Regression', confidence: 80, correctness: 48, name: 'Lasso' },
  { concept: 'Random Forests', confidence: 55, correctness: 68, name: 'RF' },
];

const CHART_COLORS = {
  mcq: '#4f46e5',
  applied: '#10b981',
  indigo: '#4f46e5',
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 shadow-sm text-xs">
      <div className="font-medium text-slate-700 mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="flex gap-2 items-center">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-slate-500">{p.name}:</span>
          <span className="font-semibold text-slate-800">{p.value}%</span>
        </div>
      ))}
    </div>
  );
}

function ScatterTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 shadow-sm text-xs">
      <div className="font-semibold text-slate-800 mb-1">{d.concept}</div>
      <div>Confidence: {d.confidence}%</div>
      <div>Correctness: {d.correctness}%</div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [timeFilter, setTimeFilter] = useState('all');

  return (
    <div className="max-w-5xl mx-auto px-8 py-10 space-y-8">
      <SectionHeader title="Analytics" subtitle="Evidence-based view of your learning activity and progress" />

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Materials" value={5} icon={<FileText size={16} />} />
        <StatCard label="Concepts" value={184} icon={<Brain size={16} />} />
        <StatCard label="Quiz Attempts" value={42} icon={<HelpCircle size={16} />} />
        <StatCard label="Flashcards" value={118} icon={<CreditCard size={16} />} />
        <StatCard label="Tutor Q&A" value={23} icon={<MessageCircle size={16} />} />
        <StatCard label="Assessments" value={9} icon={<ClipboardCheck size={16} />} />
      </div>

      {/* Mastery over time */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="text-sm font-semibold text-slate-800">Mastery Over Time</div>
            <div className="text-xs text-slate-400 mt-0.5">MCQ and Applied mastery trends from your quiz and assessment history</div>
          </div>
          <div className="flex gap-1">
            {['2w', '1m', 'all'].map(f => (
              <button
                key={f}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${timeFilter === f ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:bg-slate-100'}`}
                onClick={() => setTimeFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={MASTERY_OVER_TIME} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="mcqGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="appliedGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} domain={[0, 100]} />
            <Tooltip content={<CustomTooltip />} />
            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: '#64748b' }} />
            <Area type="monotone" dataKey="mcq" name="MCQ" stroke="#4f46e5" strokeWidth={2} fill="url(#mcqGrad)" dot={{ r: 3, fill: '#4f46e5' }} />
            <Area type="monotone" dataKey="applied" name="Applied" stroke="#10b981" strokeWidth={2} fill="url(#appliedGrad)" dot={{ r: 3, fill: '#10b981' }} />
          </AreaChart>
        </ResponsiveContainer>
        <div className="mt-3 text-xs text-slate-400 text-center">
          7 data points — keep studying to reveal a more reliable trend
        </div>
      </div>

      {/* MCQ vs Applied by topic */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="text-sm font-semibold text-slate-800 mb-1">MCQ vs. Applied Mastery by Topic</div>
        <div className="text-xs text-slate-400 mb-5">The gap between these bars reveals recognition vs. application ability</div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={TOPIC_MASTERY} margin={{ top: 5, right: 10, left: -20, bottom: 0 }} barCategoryGap="30%">
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
            <XAxis dataKey="topic" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} domain={[0, 100]} />
            <Tooltip content={<CustomTooltip />} />
            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: '#64748b' }} />
            <Bar dataKey="mcq" name="MCQ" fill="#4f46e5" radius={[3, 3, 0, 0]} />
            <Bar dataKey="applied" name="Applied" fill="#10b981" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Confidence vs Correctness scatter */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="text-sm font-semibold text-slate-800 mb-1">Confidence vs. Correctness</div>
        <div className="text-xs text-slate-400 mb-4">Each point is a concept. Points in the top-left quadrant (high confidence, low correctness) represent critical mismatches.</div>
        <div className="relative">
          <ResponsiveContainer width="100%" height={260}>
            <ScatterChart margin={{ top: 10, right: 20, left: -10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis type="number" dataKey="confidence" name="Confidence" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} domain={[0, 100]} label={{ value: 'Confidence →', position: 'insideBottomRight', offset: -5, fontSize: 11, fill: '#94a3b8' }} />
              <YAxis type="number" dataKey="correctness" name="Correctness" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} domain={[0, 100]} label={{ value: 'Correctness →', angle: -90, position: 'insideLeft', offset: 15, fontSize: 11, fill: '#94a3b8' }} />
              <ReferenceLine x={50} stroke="#e2e8f0" strokeDasharray="4 4" />
              <ReferenceLine y={50} stroke="#e2e8f0" strokeDasharray="4 4" />
              <Tooltip content={<ScatterTooltip />} />
              <Scatter data={CONFIDENCE_CORRECTNESS}>
                {CONFIDENCE_CORRECTNESS.map((d, i) => {
                  const mismatch = d.confidence > 60 && d.correctness < 65;
                  const strong = d.confidence > 60 && d.correctness >= 65;
                  const under = d.confidence <= 60 && d.correctness >= 65;
                  return <Cell key={i} fill={mismatch ? '#f97316' : strong ? '#4f46e5' : under ? '#10b981' : '#94a3b8'} />;
                })}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-wrap gap-4 mt-2 text-xs">
          {[
            { label: 'Strong understanding', color: 'bg-indigo-500' },
            { label: 'Critical mismatch', color: 'bg-orange-500' },
            { label: 'Underconfidence', color: 'bg-emerald-500' },
            { label: 'Needs practice', color: 'bg-slate-400' },
          ].map(l => (
            <div key={l.label} className="flex items-center gap-1.5">
              <div className={`w-2.5 h-2.5 rounded-full ${l.color}`} />
              <span className="text-slate-500">{l.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Before vs Now */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="text-sm font-semibold text-slate-800 mb-4">Before vs. Now</div>
        <div className="grid sm:grid-cols-3 gap-4">
          {[
            { concept: 'Gradient Descent', earlyMcq: 42, earlyApplied: 25, currentMcq: 76, currentApplied: 59 },
            { concept: 'Linear Regression', earlyMcq: 58, earlyApplied: 40, currentMcq: 94, currentApplied: 88 },
            { concept: 'Decision Trees', earlyMcq: 64, earlyApplied: 50, currentMcq: 91, currentApplied: 84 },
          ].map(item => (
            <div key={item.concept} className="border border-slate-100 rounded-xl p-4">
              <div className="text-xs font-semibold text-slate-600 mb-3">{item.concept}</div>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div>
                  <div className="text-xs text-slate-400 mb-1">Earlier</div>
                  <div className="text-xs font-mono-data text-slate-500">MCQ {item.earlyMcq}%</div>
                  <div className="text-xs font-mono-data text-slate-500">Applied {item.earlyApplied}%</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400 mb-1">Current</div>
                  <div className="text-xs font-mono-data text-green-600 font-semibold">MCQ {item.currentMcq}%</div>
                  <div className="text-xs font-mono-data text-green-600 font-semibold">Applied {item.currentApplied}%</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
