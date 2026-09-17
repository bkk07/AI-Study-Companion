import React, { useState } from 'react';
import { ChevronLeft, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react';
import { QUIZ_QUESTIONS } from '../../data/mockData';
import { SectionHeader } from '../../components/ui';
import type { QuizQuestion } from '../../types';

type QuizState = 'setup' | 'question' | 'results';

interface Answer {
  questionId: string;
  selectedIndex: number;
  confidence: 'low' | 'medium' | 'high';
  correct: boolean;
}

export default function QuizPage() {
  const [quizState, setQuizState] = useState<QuizState>('setup');
  const [questionIndex, setQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [selectedConfidence, setSelectedConfidence] = useState<'low' | 'medium' | 'high' | null>(null);
  const [scope, setScope] = useState('project');
  const [qCount, setQCount] = useState(5);

  const questions = QUIZ_QUESTIONS.slice(0, qCount);
  const current = questions[questionIndex];

  const handleNext = () => {
    if (selectedAnswer === null || !selectedConfidence) return;
    const answer: Answer = {
      questionId: current.id,
      selectedIndex: selectedAnswer,
      confidence: selectedConfidence,
      correct: selectedAnswer === current.correctIndex,
    };
    const newAnswers = [...answers, answer];
    setAnswers(newAnswers);
    setSelectedAnswer(null);
    setSelectedConfidence(null);
    if (questionIndex < questions.length - 1) {
      setQuestionIndex(i => i + 1);
    } else {
      setQuizState('results');
    }
  };

  const reset = () => {
    setQuizState('setup');
    setQuestionIndex(0);
    setAnswers([]);
    setSelectedAnswer(null);
    setSelectedConfidence(null);
  };

  if (quizState === 'setup') return <SetupView scope={scope} setScope={setScope} qCount={qCount} setQCount={setQCount} onStart={() => setQuizState('question')} />;
  if (quizState === 'results') return <ResultsView questions={questions} answers={answers} onReset={reset} />;

  return (
    <div className="max-w-2xl mx-auto px-8 py-10">
      {/* Progress */}
      <div className="mb-8">
        <div className="flex justify-between text-sm text-slate-500 mb-2">
          <span>Question {questionIndex + 1} / {questions.length}</span>
          <button className="text-slate-400 hover:text-slate-600 text-xs" onClick={reset}>Exit quiz</button>
        </div>
        <div className="h-1.5 bg-slate-100 rounded-full">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all"
            style={{ width: `${((questionIndex) / questions.length) * 100}%` }}
          />
        </div>
        <div className="mt-2 text-xs text-slate-400 bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 flex gap-2">
          <Info size={12} className="flex-shrink-0 mt-0.5" />
          <span><strong className="text-slate-500">Why this question?</strong> {current.reason}</span>
        </div>
      </div>

      {/* Question */}
      <div className="bg-white border border-slate-200 rounded-xl p-7 mb-5">
        <p className="text-base font-medium text-slate-800 leading-relaxed mb-6">{current.stem}</p>
        <div className="space-y-3">
          {current.options.map((opt, i) => (
            <button
              key={i}
              className={`w-full text-left px-4 py-3.5 rounded-xl border text-sm transition-all ${
                selectedAnswer === i
                  ? 'border-indigo-500 bg-indigo-50 text-indigo-800'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700'
              }`}
              onClick={() => setSelectedAnswer(i)}
            >
              <span className={`inline-flex w-6 h-6 rounded-full items-center justify-center text-xs font-bold mr-3 ${
                selectedAnswer === i ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-500'
              }`}>
                {String.fromCharCode(65 + i)}
              </span>
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Confidence — visually distinct */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 mb-5">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-px h-4 bg-slate-300" />
          <p className="text-sm font-semibold text-slate-700">How confident are you in your answer?</p>
        </div>
        <div className="flex gap-2">
          {(['low', 'medium', 'high'] as const).map(level => (
            <button
              key={level}
              className={`flex-1 py-2.5 rounded-lg border text-sm font-medium capitalize transition-all ${
                selectedConfidence === level
                  ? level === 'low'
                    ? 'border-red-300 bg-red-50 text-red-700'
                    : level === 'medium'
                    ? 'border-amber-300 bg-amber-50 text-amber-700'
                    : 'border-green-300 bg-green-50 text-green-700'
                  : 'border-slate-200 text-slate-500 hover:border-slate-300 bg-white'
              }`}
              onClick={() => setSelectedConfidence(level)}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      <button
        className="w-full py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        onClick={handleNext}
        disabled={selectedAnswer === null || !selectedConfidence}
      >
        {questionIndex < questions.length - 1 ? 'Next question' : 'See results'}
      </button>
    </div>
  );
}

function SetupView({ scope, setScope, qCount, setQCount, onStart }: {
  scope: string; setScope: (s: string) => void;
  qCount: number; setQCount: (n: number) => void;
  onStart: () => void;
}) {
  return (
    <div className="max-w-lg mx-auto px-8 py-10">
      <SectionHeader title="Adaptive Quiz" subtitle="Questions are selected based on your mastery evidence" />
      <div className="bg-white border border-slate-200 rounded-xl p-8 space-y-6">
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-2.5">Quiz scope</label>
          <div className="flex flex-wrap gap-2">
            {['project', 'topic', 'subtopic', 'concept'].map(s => (
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
          <label className="text-sm font-medium text-slate-700 block mb-2.5">Number of questions</label>
          <div className="flex gap-2">
            {[5, 10, 20].map(n => (
              <button
                key={n}
                className={`px-5 py-1.5 rounded-lg border text-sm transition-colors ${qCount === n ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-slate-200 text-slate-600 hover:border-slate-300'}`}
                onClick={() => setQCount(n)}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700 block mb-1">Difficulty</label>
          <div className="text-sm text-slate-500 bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2">
            Adaptive — questions are chosen based on mastery evidence and detected mismatches
          </div>
        </div>

        <div className="text-xs text-slate-400 flex items-center gap-1.5">
          <Info size={12} />
          Estimated time: {qCount * 1.5} minutes
        </div>

        <button
          className="w-full py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors"
          onClick={onStart}
        >
          Start Quiz
        </button>
      </div>
    </div>
  );
}

function ResultsView({ questions, answers, onReset }: { questions: QuizQuestion[]; answers: Answer[]; onReset: () => void }) {
  const correct = answers.filter(a => a.correct).length;
  const score = Math.round((correct / answers.length) * 100);

  const mismatches = answers.filter(a => !a.correct && a.confidence === 'high');
  const underconfident = answers.filter(a => a.correct && a.confidence === 'low');
  const strong = answers.filter(a => a.correct && a.confidence === 'high');

  const quadrant = (correct: boolean, confidence: 'low' | 'medium' | 'high') => {
    if (correct && confidence === 'high') return 'Strong understanding';
    if (correct && confidence !== 'high') return 'Underconfidence';
    if (!correct && confidence === 'high') return 'Critical mismatch';
    return 'Needs practice';
  };

  return (
    <div className="max-w-2xl mx-auto px-8 py-10">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-slate-900">Quiz Results</h2>
        <button className="text-sm text-indigo-600 hover:underline" onClick={onReset}>Retake quiz</button>
      </div>

      {/* Score */}
      <div className="bg-white border border-slate-200 rounded-xl p-8 mb-5 flex items-center gap-8">
        <div className="text-center">
          <div className={`text-5xl font-bold font-mono-data ${score >= 70 ? 'text-green-600' : score >= 50 ? 'text-amber-600' : 'text-red-600'}`}>{score}%</div>
          <div className="text-sm text-slate-500 mt-1">Score</div>
        </div>
        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2 text-green-600"><CheckCircle size={14} />Correct</span>
            <span className="font-mono-data font-semibold text-slate-800">{correct} / {answers.length}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2 text-red-500"><XCircle size={14} />Incorrect</span>
            <span className="font-mono-data font-semibold text-slate-800">{answers.length - correct} / {answers.length}</span>
          </div>
          {mismatches.length > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2 text-amber-600"><AlertTriangle size={14} />Mismatches</span>
              <span className="font-mono-data font-semibold text-slate-800">{mismatches.length}</span>
            </div>
          )}
        </div>
      </div>

      {/* Mismatch alert */}
      {mismatches.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-5">
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-semibold text-amber-800 mb-1">Confidence Mismatch Detected</div>
              <p className="text-sm text-amber-700">
                You answered <strong>{mismatches.length} question{mismatches.length > 1 ? 's' : ''}</strong> incorrectly with <strong>High confidence</strong>. This is a diagnostic signal — your mental model of {mismatches.map(m => questions.find(q => q.id === m.questionId)?.conceptName).join(', ')} may need correction, not just more practice.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Per-question breakdown */}
      <div className="space-y-3 mb-6">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Confidence vs. Correctness</div>
        {answers.map((answer, i) => {
          const q = questions[i];
          if (!q) return null;
          const quad = quadrant(answer.correct, answer.confidence);
          return (
            <div key={answer.questionId} className="bg-white border border-slate-200 rounded-xl px-5 py-4">
              <div className="flex items-start gap-3">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${answer.correct ? 'bg-green-100' : 'bg-red-100'}`}>
                  {answer.correct ? <CheckCircle size={14} className="text-green-600" /> : <XCircle size={14} className="text-red-500" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-700 line-clamp-2 mb-1">{q.stem}</p>
                  <div className="flex gap-3 text-xs">
                    <span className={answer.correct ? 'text-green-600' : 'text-red-500'}>{answer.correct ? 'Correct' : 'Incorrect'}</span>
                    <span className="text-slate-400">·</span>
                    <span className="text-slate-500">{answer.confidence} confidence</span>
                    <span className="text-slate-400">·</span>
                    <span className={`font-medium ${
                      quad === 'Strong understanding' ? 'text-green-600' :
                      quad === 'Critical mismatch' ? 'text-red-600' :
                      quad === 'Underconfidence' ? 'text-blue-600' : 'text-slate-500'
                    }`}>{quad}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <button
        className="w-full py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors"
        onClick={onReset}
      >
        Try another quiz
      </button>
    </div>
  );
}
