import React, { useState } from 'react';
import { ChevronRight, ChevronDown, MessageCircle, HelpCircle, CreditCard, Info } from 'lucide-react';
import { TOPICS } from '../../data/mockData';
import { MasteryBadge, MasteryDot, SectionHeader } from '../../components/ui';
import { useApp } from '../../context/AppContext';
import type { Concept, MasteryLevel, Subtopic, Topic } from '../../types';

function ConceptRow({ concept, onClick }: { concept: Concept; onClick: () => void }) {
  const masteryColors: Record<MasteryLevel, string> = {
    mastered: 'border-green-100 hover:border-green-200',
    developing: 'border-amber-100 hover:border-amber-200',
    weak: 'border-red-100 hover:border-red-200',
    unassessed: 'border-slate-100 hover:border-slate-200',
  };
  return (
    <div
      className={`flex items-center gap-4 px-4 py-3 bg-white border rounded-lg cursor-pointer transition-all hover:shadow-sm ${masteryColors[concept.mastery]}`}
      onClick={onClick}
    >
      <MasteryDot level={concept.mastery} />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-slate-800 truncate">{concept.name}</div>
        {concept.mastery !== 'unassessed' && (
          <div className="flex gap-3 mt-0.5 text-xs font-mono-data">
            <span className="text-slate-400">MCQ <span className="text-slate-600">{concept.mcqMastery}%</span></span>
            <span className="text-slate-400">Applied <span className="text-slate-600">{concept.appliedMastery}%</span></span>
          </div>
        )}
        {concept.mastery === 'unassessed' && (
          <div className="text-xs text-slate-400 mt-0.5">Not assessed yet</div>
        )}
      </div>
      <MasteryBadge level={concept.mastery} />
      {concept.lastPracticed && (
        <span className="text-xs text-slate-400 hidden sm:block whitespace-nowrap">{concept.lastPracticed}</span>
      )}
    </div>
  );
}

function SubtopicSection({ subtopic, onConceptClick }: { subtopic: Subtopic; onConceptClick: (c: Concept) => void }) {
  const [open, setOpen] = useState(true);
  return (
    <div>
      <button
        className="flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-800 py-2 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {subtopic.name}
        <span className="ml-1 text-xs text-slate-400 font-normal">{subtopic.concepts.length} concepts</span>
      </button>
      {open && (
        <div className="ml-6 space-y-2 mt-1 mb-3">
          {subtopic.concepts.map(c => (
            <ConceptRow key={c.id} concept={c} onClick={() => onConceptClick(c)} />
          ))}
        </div>
      )}
    </div>
  );
}

function TopicSection({ topic, onConceptClick }: { topic: Topic; onConceptClick: (c: Concept) => void }) {
  const [open, setOpen] = useState(true);
  const allC = topic.subtopics.flatMap(s => s.concepts);
  const masteredC = allC.filter(c => c.mastery === 'mastered').length;
  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-6 py-4 hover:bg-slate-50 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        {open ? <ChevronDown size={16} className="text-slate-400" /> : <ChevronRight size={16} className="text-slate-400" />}
        <span className="text-base font-semibold text-slate-900 flex-1 text-left">{topic.name}</span>
        <span className="text-xs text-slate-400 font-mono-data">{masteredC}/{allC.length} mastered</span>
      </button>
      {open && (
        <div className="px-6 pb-4 border-t border-slate-100 pt-4 space-y-1">
          {topic.subtopics.map(s => (
            <SubtopicSection key={s.id} subtopic={s} onConceptClick={onConceptClick} />
          ))}
        </div>
      )}
    </div>
  );
}

function ConceptPanel({ concept, onClose }: { concept: Concept; onClose: () => void }) {
  const { navigate } = useApp();
  const evidenceTimeline = [
    { action: 'Quiz', result: 'Correct', confidence: 'High', time: '25 min ago' },
    { action: 'Assessment', result: 'Incorrect', confidence: 'High', time: '2 days ago' },
    { action: 'Flashcard', result: 'Correct', confidence: null, time: '3 days ago' },
    { action: 'Quiz', result: 'Incorrect', confidence: 'High', time: '5 days ago' },
    { action: 'Quiz', result: 'Correct', confidence: 'Medium', time: '1 week ago' },
  ];

  return (
    <div className="fixed right-0 top-14 bottom-0 w-96 bg-white border-l border-slate-200 overflow-y-auto z-40 shadow-xl">
      <div className="p-6">
        <div className="flex items-start justify-between mb-5">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">{concept.name}</h3>
            <div className="text-xs text-slate-400 mt-1">{concept.source.document} · p.{concept.source.page}</div>
          </div>
          <button className="text-slate-400 hover:text-slate-600 text-lg leading-none" onClick={onClose}>×</button>
        </div>

        <p className="text-sm text-slate-600 leading-relaxed mb-5">{concept.description}</p>

        <MasteryBadge level={concept.mastery} size="md" />

        {concept.mastery !== 'unassessed' ? (
          <>
            <div className="grid grid-cols-2 gap-3 mt-5">
              <div className="bg-green-50 border border-green-100 rounded-lg px-4 py-3">
                <div className="text-xl font-bold font-mono-data text-green-700">{concept.mcqMastery}%</div>
                <div className="text-xs text-slate-500 mt-0.5">MCQ Mastery</div>
              </div>
              <div className="bg-amber-50 border border-amber-100 rounded-lg px-4 py-3">
                <div className="text-xl font-bold font-mono-data text-amber-700">{concept.appliedMastery}%</div>
                <div className="text-xs text-slate-500 mt-0.5">Applied Mastery</div>
              </div>
            </div>
            {concept.mcqMastery && concept.appliedMastery && concept.mcqMastery - concept.appliedMastery > 20 && (
              <div className="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 flex gap-2">
                <Info size={13} className="flex-shrink-0 mt-0.5" />
                You can recognize this concept but need more practice applying it.
              </div>
            )}
            <div className="mt-5 grid grid-cols-3 gap-2 text-center">
              {[
                { label: 'Quiz attempts', value: concept.quizAttempts },
                { label: 'Assessments', value: concept.appliedAssessments },
                { label: 'Flashcards', value: concept.flashcardReviews },
              ].map(e => (
                <div key={e.label} className="bg-slate-50 rounded-lg px-2 py-3">
                  <div className="font-mono-data font-semibold text-slate-800 text-base">{e.value}</div>
                  <div className="text-xs text-slate-400 mt-0.5 leading-tight">{e.label}</div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="mt-4 text-sm text-slate-500 bg-slate-50 border border-slate-100 rounded-lg p-4">
            This concept has not been assessed yet. Start practicing to build mastery evidence.
          </div>
        )}

        <div className="flex flex-wrap gap-2 mt-5">
          <button className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 transition-colors" onClick={() => navigate('tutor')}>
            <MessageCircle size={12} />Ask Tutor
          </button>
          <button className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 bg-slate-50 text-slate-700 rounded-lg hover:bg-slate-100 transition-colors" onClick={() => navigate('quiz')}>
            <HelpCircle size={12} />Quiz Me
          </button>
          <button className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 bg-slate-50 text-slate-700 rounded-lg hover:bg-slate-100 transition-colors" onClick={() => navigate('flashcards')}>
            <CreditCard size={12} />Flashcards
          </button>
        </div>

        {concept.mastery !== 'unassessed' && (
          <div className="mt-6">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Learning Evidence</div>
            <div className="space-y-2.5">
              {evidenceTimeline.map((e, i) => (
                <div key={i} className="flex items-center gap-3 text-xs">
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                    e.result === 'Correct' ? 'bg-green-500' : 'bg-red-400'
                  }`} />
                  <span className="font-medium text-slate-600">{e.action}</span>
                  <span className={e.result === 'Correct' ? 'text-green-600' : 'text-red-500'}>{e.result}</span>
                  {e.confidence && <span className="text-slate-400">· {e.confidence} confidence</span>}
                  <span className="text-slate-300 ml-auto">{e.time}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function StructurePage() {
  const [selectedConcept, setSelectedConcept] = useState<Concept | null>(null);

  const allC = TOPICS.flatMap(t => t.subtopics.flatMap(s => s.concepts));
  const counts = {
    mastered: allC.filter(c => c.mastery === 'mastered').length,
    developing: allC.filter(c => c.mastery === 'developing').length,
    weak: allC.filter(c => c.mastery === 'weak').length,
    unassessed: allC.filter(c => c.mastery === 'unassessed').length,
  };

  return (
    <div className={`px-8 py-10 transition-all ${selectedConcept ? 'mr-96' : ''}`}>
      <div className="max-w-3xl mx-auto">
        <SectionHeader title="Knowledge Map" subtitle="Explore your learning structure and mastery" />

        <div className="flex gap-4 mb-6 flex-wrap">
          {[
            { label: 'Mastered', value: counts.mastered, cls: 'text-green-600' },
            { label: 'Developing', value: counts.developing, cls: 'text-amber-600' },
            { label: 'Weak', value: counts.weak, cls: 'text-red-600' },
            { label: 'Not Assessed', value: counts.unassessed, cls: 'text-slate-400' },
          ].map(s => (
            <div key={s.label} className="flex items-center gap-2 text-sm">
              <span className={`font-semibold font-mono-data ${s.cls}`}>{s.value}</span>
              <span className="text-slate-500">{s.label}</span>
            </div>
          ))}
        </div>

        <div className="space-y-4">
          {TOPICS.map(topic => (
            <TopicSection key={topic.id} topic={topic} onConceptClick={setSelectedConcept} />
          ))}
        </div>
      </div>
      {selectedConcept && (
        <ConceptPanel concept={selectedConcept} onClose={() => setSelectedConcept(null)} />
      )}
    </div>
  );
}
