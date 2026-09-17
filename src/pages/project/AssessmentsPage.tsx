import React, { useState } from 'react';
import { CheckCircle, AlertCircle, XCircle, ChevronRight, Info } from 'lucide-react';
import { SectionHeader, Button } from '../../components/ui';

type AssessmentState = 'prompt' | 'writing' | 'confidence' | 'result';

const PROMPTS = [
  { id: 'p1', concept: 'Gradient Descent', text: 'Explain gradient descent as if you were teaching it to another student.' },
  { id: 'p2', concept: 'Logistic Regression', text: 'Describe how logistic regression works and when you would use it over linear regression.' },
  { id: 'p3', concept: 'Regularization', text: 'Explain the difference between L1 and L2 regularization and when each is preferable.' },
];

interface EvaluationResult {
  covered: { item: string; note: string }[];
  missing: { item: string; note: string }[];
  misconceptions: { item: string; note: string }[];
  quality: 'strong' | 'adequate' | 'developing';
  suggestion: string;
  confidence: 'low' | 'medium' | 'high';
  understanding: 'mastered' | 'developing' | 'weak';
}

const SAMPLE_RESULT: EvaluationResult = {
  covered: [
    { item: 'Iterative optimization', note: 'Correctly identified as an iterative process' },
    { item: 'Loss function minimization', note: 'Clear connection to minimizing error' },
    { item: 'Parameter updates', note: 'Described updating weights in each step' },
  ],
  missing: [
    { item: 'Learning rate', note: 'Not mentioned — this is a critical hyperparameter controlling step size' },
    { item: 'Local vs. global minima', note: 'Important consideration for non-convex loss landscapes' },
  ],
  misconceptions: [
    { item: 'Direction of gradient', note: '"Move in the direction of the gradient" is incorrect — gradient descent moves opposite to the gradient' },
  ],
  quality: 'developing',
  suggestion: 'Review the learning rate section (Machine Learning Notes.pdf, p.114–118) and try explaining gradient descent again with a focus on the step size and direction.',
  confidence: 'high',
  understanding: 'developing',
};

export default function AssessmentsPage() {
  const [assessState, setAssessState] = useState<AssessmentState>('prompt');
  const [selectedPrompt, setSelectedPrompt] = useState(PROMPTS[0]);
  const [answer, setAnswer] = useState('');
  const [confidence, setConfidence] = useState<'low' | 'medium' | 'high' | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [result, setResult] = useState<EvaluationResult | null>(null);

  const handleSubmit = async () => {
    if (!answer.trim()) return;
    setAssessState('confidence');
  };

  const handleEvaluate = async () => {
    if (!confidence) return;
    setEvaluating(true);
    await new Promise(r => setTimeout(r, 2000));
    setEvaluating(false);
    setResult({ ...SAMPLE_RESULT, confidence });
    setAssessState('result');
  };

  const reset = () => {
    setAssessState('prompt');
    setAnswer('');
    setConfidence(null);
    setResult(null);
  };

  return (
    <div className="max-w-2xl mx-auto px-8 py-10">
      <SectionHeader title="Assessments" subtitle="Explain concepts in your own words — AI evaluates against source material" />

      {assessState === 'prompt' && (
        <div className="space-y-4">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Select a prompt</div>
          {PROMPTS.map(prompt => (
            <div
              key={prompt.id}
              className={`bg-white border rounded-xl p-5 cursor-pointer transition-all ${
                selectedPrompt.id === prompt.id ? 'border-indigo-300 ring-1 ring-indigo-100' : 'border-slate-200 hover:border-slate-300'
              }`}
              onClick={() => setSelectedPrompt(prompt)}
            >
              <div className="text-xs text-indigo-600 font-medium mb-1">{prompt.concept}</div>
              <p className="text-sm text-slate-700 leading-relaxed">{prompt.text}</p>
            </div>
          ))}
          <Button
            variant="primary"
            onClick={() => setAssessState('writing')}
            className="w-full justify-center mt-2"
          >
            Start assessment
          </Button>
        </div>
      )}

      {assessState === 'writing' && (
        <div>
          <div className="bg-white border border-slate-200 rounded-xl p-6 mb-4">
            <div className="text-xs text-indigo-600 font-semibold mb-2">{selectedPrompt.concept}</div>
            <h3 className="text-base font-medium text-slate-800 leading-relaxed mb-5">{selectedPrompt.text}</h3>
            <textarea
              className="w-full h-52 text-sm text-slate-700 border border-slate-200 rounded-lg p-4 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-50 resize-none placeholder:text-slate-400 transition"
              placeholder="Write your explanation here…"
              value={answer}
              onChange={e => setAnswer(e.target.value)}
            />
            <div className="flex justify-between items-center mt-2">
              <span className="text-xs text-slate-400">{answer.length > 0 ? `${answer.split(/\s+/).filter(Boolean).length} words` : 'Aim for 100–200 words'}</span>
              <Button variant="primary" onClick={handleSubmit} disabled={answer.trim().length < 20}>
                Submit <ChevronRight size={14} />
              </Button>
            </div>
          </div>
          <button className="text-xs text-slate-400 hover:text-slate-600" onClick={reset}>← Back to prompts</button>
        </div>
      )}

      {assessState === 'confidence' && (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
          <div className="text-sm font-semibold text-slate-700 mb-1">Before we evaluate…</div>
          <p className="text-sm text-slate-500 mb-8">How confident are you in your explanation of {selectedPrompt.concept}?</p>
          <div className="flex gap-3 justify-center mb-8">
            {(['low', 'medium', 'high'] as const).map(c => (
              <button
                key={c}
                className={`px-8 py-3 rounded-xl border text-sm font-semibold capitalize transition-all ${
                  confidence === c
                    ? c === 'low' ? 'border-red-300 bg-red-50 text-red-700' : c === 'medium' ? 'border-amber-300 bg-amber-50 text-amber-700' : 'border-green-300 bg-green-50 text-green-700'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
                onClick={() => setConfidence(c)}
              >
                {c}
              </button>
            ))}
          </div>
          <Button
            variant="primary"
            onClick={handleEvaluate}
            disabled={!confidence || evaluating}
            className="w-full justify-center"
          >
            {evaluating ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Evaluating against source material…
              </>
            ) : 'Get AI evaluation'}
          </Button>
        </div>
      )}

      {assessState === 'result' && result && (
        <div className="space-y-5">
          {/* Confidence vs understanding */}
          <div className={`border rounded-xl p-5 ${
            result.confidence === 'high' && result.understanding !== 'mastered'
              ? 'bg-amber-50 border-amber-200'
              : 'bg-slate-50 border-slate-200'
          }`}>
            <div className="flex gap-6 mb-3">
              <div className="text-center">
                <div className="text-xs text-slate-500 mb-1">Reported Confidence</div>
                <div className={`text-sm font-semibold capitalize ${result.confidence === 'high' ? 'text-green-600' : result.confidence === 'medium' ? 'text-amber-600' : 'text-slate-600'}`}>
                  {result.confidence}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-slate-500 mb-1">Demonstrated Understanding</div>
                <div className={`text-sm font-semibold capitalize ${result.understanding === 'mastered' ? 'text-green-600' : result.understanding === 'developing' ? 'text-amber-600' : 'text-red-600'}`}>
                  {result.understanding}
                </div>
              </div>
            </div>
            {result.confidence === 'high' && result.understanding !== 'mastered' && (
              <div className="flex gap-2 text-xs text-amber-800">
                <Info size={13} className="flex-shrink-0 mt-0.5" />
                Your confidence appears higher than your demonstrated understanding. This is valuable to know — study the missing concepts deliberately.
              </div>
            )}
          </div>

          {/* Understanding analysis */}
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-slate-800 mb-4">Understanding Analysis</h3>
            <div className="space-y-4">
              {result.covered.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-green-600 uppercase tracking-wider mb-2">Covered correctly</div>
                  <div className="space-y-2">
                    {result.covered.map((item, i) => (
                      <div key={i} className="flex gap-3 text-sm">
                        <CheckCircle size={14} className="text-green-500 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="font-medium text-slate-700">{item.item}</span>
                          <p className="text-slate-400 text-xs mt-0.5">{item.note}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.missing.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-amber-600 uppercase tracking-wider mb-2">Missing concepts</div>
                  <div className="space-y-2">
                    {result.missing.map((item, i) => (
                      <div key={i} className="flex gap-3 text-sm">
                        <AlertCircle size={14} className="text-amber-500 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="font-medium text-slate-700">{item.item}</span>
                          <p className="text-slate-400 text-xs mt-0.5">{item.note}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.misconceptions.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-red-600 uppercase tracking-wider mb-2">Misconceptions detected</div>
                  <div className="space-y-2">
                    {result.misconceptions.map((item, i) => (
                      <div key={i} className="flex gap-3 text-sm">
                        <XCircle size={14} className="text-red-500 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="font-medium text-slate-700">{item.item}</span>
                          <p className="text-slate-400 text-xs mt-0.5">{item.note}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Next step */}
          <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
            <div className="text-xs font-semibold text-indigo-600 uppercase tracking-wider mb-2">Suggested Next Step</div>
            <p className="text-sm text-slate-700">{result.suggestion}</p>
          </div>

          <div className="flex gap-3">
            <Button variant="primary" onClick={reset} className="flex-1 justify-center">Try another assessment</Button>
            <Button variant="secondary" onClick={() => { setAnswer(''); setAssessState('writing'); }}>Re-attempt this prompt</Button>
          </div>
        </div>
      )}
    </div>
  );
}
