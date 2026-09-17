import React, { useState } from 'react';
import { CheckCircle, Layers, MessageCircle, Pen, Upload, HelpCircle } from 'lucide-react';
import { ACTIVITY_EVENTS } from '../../data/mockData';
import { SectionHeader, EmptyState } from '../../components/ui';

type FilterType = 'all' | 'quiz' | 'flashcard' | 'tutor' | 'assessment' | 'document';

const ICON_MAP: Record<string, React.ReactNode> = {
  'check-circle': <CheckCircle size={14} />,
  'layers': <Layers size={14} />,
  'message-circle': <MessageCircle size={14} />,
  'pen-line': <Pen size={14} />,
  'upload': <Upload size={14} />,
  'help-circle': <HelpCircle size={14} />,
};

const TYPE_COLORS: Record<string, string> = {
  quiz: 'bg-indigo-50 text-indigo-600 border-indigo-100',
  flashcard: 'bg-amber-50 text-amber-600 border-amber-100',
  tutor: 'bg-blue-50 text-blue-600 border-blue-100',
  assessment: 'bg-green-50 text-green-600 border-green-100',
  document: 'bg-slate-50 text-slate-600 border-slate-200',
};

export default function ActivityPage() {
  const [filter, setFilter] = useState<FilterType>('all');

  const filterLabels: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'quiz', label: 'Quiz' },
    { key: 'flashcard', label: 'Flashcards' },
    { key: 'tutor', label: 'Tutor' },
    { key: 'assessment', label: 'Assessments' },
    { key: 'document', label: 'Documents' },
  ];

  const filteredDays = ACTIVITY_EVENTS.map(day => ({
    ...day,
    events: day.events.filter(e => filter === 'all' || e.type === filter),
  })).filter(day => day.events.length > 0);

  return (
    <div className="max-w-2xl mx-auto px-8 py-10">
      <SectionHeader title="Learning Activity" subtitle="A chronological record of your study sessions" />

      {/* Filters */}
      <div className="flex gap-1 mb-8 overflow-x-auto pb-1">
        {filterLabels.map(fl => (
          <button
            key={fl.key}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              filter === fl.key ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:bg-slate-100'
            }`}
            onClick={() => setFilter(fl.key)}
          >
            {fl.label}
          </button>
        ))}
      </div>

      {filteredDays.length === 0 ? (
        <EmptyState
          icon={<CheckCircle size={22} />}
          title="No activity found"
          description="Start studying to see your learning history here."
        />
      ) : (
        <div className="space-y-8">
          {filteredDays.map(day => (
            <div key={day.id}>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">{day.date}</div>
              <div className="space-y-2">
                {day.events.map((event, i) => (
                  <div key={i} className="flex items-start gap-4 bg-white border border-slate-100 rounded-xl px-4 py-3.5 hover:border-slate-200 transition-colors">
                    <div className={`w-8 h-8 rounded-lg border flex items-center justify-center flex-shrink-0 mt-0.5 ${TYPE_COLORS[event.type] ?? 'bg-slate-50 text-slate-500 border-slate-200'}`}>
                      {ICON_MAP[event.icon] ?? <CheckCircle size={14} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-800 font-medium">{event.label}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{event.detail}</p>
                    </div>
                    <span className="text-xs text-slate-400 font-mono-data flex-shrink-0 mt-0.5">{event.time}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
