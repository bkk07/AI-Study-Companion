import React, { useState, useRef, useEffect } from 'react';
import { Send, FileText, ChevronRight, Lightbulb, Repeat, BookOpen, HelpCircle, Minimize2 } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'ai';
  text: string;
  citations?: number[];
  time: string;
}

interface Source {
  id: number;
  document: string;
  page: number;
  excerpt: string;
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: 'm0',
    role: 'ai',
    text: "Hello! I'm your AI tutor for Machine Learning. I can answer questions grounded in your uploaded study material. What would you like to explore?",
    time: '9:18 AM',
  },
  {
    id: 'm1',
    role: 'user',
    text: 'What is logistic regression and how does it work?',
    time: '9:18 AM',
  },
  {
    id: 'm2',
    role: 'ai',
    text: "Logistic regression estimates the probability of a binary outcome using the logistic function.[1] Unlike linear regression, it maps predictions to a probability between 0 and 1 using the sigmoid function: σ(z) = 1 / (1 + e⁻ᶻ), where z is the linear combination of input features.[1]\n\nThe model outputs a probability, which is then thresholded (usually at 0.5) to produce a class prediction. Training involves minimising the cross-entropy loss using an optimization algorithm such as gradient descent.[2]",
    citations: [1, 2],
    time: '9:18 AM',
  },
  {
    id: 'm3',
    role: 'user',
    text: 'What is the sigmoid derivative?',
    time: '9:19 AM',
  },
  {
    id: 'm4',
    role: 'ai',
    text: "The derivative of the sigmoid function σ(z) has a particularly elegant form.[1] If σ(z) = 1 / (1 + e⁻ᶻ), then:\n\nσ'(z) = σ(z) · (1 − σ(z))\n\nThis means the derivative can be computed from the output itself, which makes backpropagation in neural networks computationally efficient.[2] Note that the sigmoid derivative reaches its maximum value of 0.25 when z = 0, which can contribute to the vanishing gradient problem in deep networks.",
    citations: [1, 2],
    time: '9:19 AM',
  },
];

const SOURCES: Source[] = [
  {
    id: 1,
    document: 'Machine Learning Notes.pdf',
    page: 42,
    excerpt: '"…logistic regression models the probability of a binary outcome using the logistic function, mapping real-valued outputs to the (0,1) interval via the sigmoid σ(z) = 1/(1+e⁻ᶻ)…"',
  },
  {
    id: 2,
    document: 'Machine Learning Notes.pdf',
    page: 115,
    excerpt: '"…gradient descent minimizes the cross-entropy loss by iteratively updating parameters in the direction opposite to the gradient, scaled by the learning rate η…"',
  },
];

const QUICK_ACTIONS = [
  { label: 'Explain simpler', icon: <Minimize2 size={13} /> },
  { label: 'Give an example', icon: <Lightbulb size={13} /> },
  { label: 'Compare concepts', icon: <Repeat size={13} /> },
  { label: 'Summarize', icon: <BookOpen size={13} /> },
  { label: 'Quiz me on this', icon: <HelpCircle size={13} /> },
];

export default function TutorPage() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeSourceIds, setActiveSourceIds] = useState<number[]>([1, 2]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim()) return;
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: text.trim(),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages(m => [...m, userMsg]);
    setInput('');
    setLoading(true);
    await new Promise(r => setTimeout(r, 1200));
    setLoading(false);
    const aiMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: 'ai',
      text: "Based on your uploaded material, this concept is explained in the context of optimization.[2] The key insight is that gradient descent updates parameters iteratively using the gradient of the loss function: θ ← θ − η∇L(θ), where η is the learning rate.[2]\n\nFor logistic regression specifically, the gradient of the cross-entropy loss with respect to the weights has a clean closed form, making it computationally tractable.[1]",
      citations: [1, 2],
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages(m => [...m, aiMsg]);
  };

  const renderText = (text: string, citations?: number[]) => {
    if (!citations) return <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{text}</p>;
    const parts = text.split(/(\[\d+\])/g);
    return (
      <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
        {parts.map((part, i) => {
          const match = part.match(/^\[(\d+)\]$/);
          if (match) {
            return (
              <sup key={i} className="text-indigo-600 font-semibold cursor-pointer hover:underline ml-0.5"
                onClick={() => setActiveSourceIds([parseInt(match[1])])}>
                {part}
              </sup>
            );
          }
          return part;
        })}
      </p>
    );
  };

  return (
    <div className="flex h-full">
      {/* Chat (70%) */}
      <div className="flex flex-col flex-1 min-w-0 border-r border-slate-200">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.map(msg => (
            <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {msg.role === 'ai' && (
                <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0">
                  <BookOpen size={14} className="text-white" />
                </div>
              )}
              <div className={`max-w-lg ${msg.role === 'user' ? 'ml-auto' : ''}`}>
                <div className={`rounded-xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white text-sm'
                    : 'bg-white border border-slate-200 text-slate-700'
                }`}>
                  {msg.role === 'ai' ? renderText(msg.text, msg.citations) : (
                    <p className="text-sm leading-relaxed">{msg.text}</p>
                  )}
                </div>
                <div className="text-xs text-slate-400 mt-1 px-1">{msg.time}</div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0">
                <BookOpen size={14} className="text-white" />
              </div>
              <div className="bg-white border border-slate-200 rounded-xl px-4 py-3">
                <div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 150}ms` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Quick actions */}
        <div className="px-6 py-2 flex gap-2 flex-wrap">
          {QUICK_ACTIONS.map(a => (
            <button
              key={a.label}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-xs text-slate-600 hover:bg-slate-100 transition-colors"
              onClick={() => send(a.label)}
            >
              {a.icon}{a.label}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="px-6 pb-6 pt-2">
          <div className="flex gap-2 bg-white border border-slate-200 rounded-xl p-3 focus-within:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-50 transition">
            <input
              className="flex-1 text-sm text-slate-800 outline-none placeholder:text-slate-400"
              placeholder="Ask a question about your study material…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); } }}
            />
            <button
              className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white hover:bg-indigo-700 transition-colors disabled:opacity-40"
              onClick={() => send(input)}
              disabled={!input.trim() || loading}
            >
              <Send size={14} />
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-2 text-center">
            Answers are generated only from your uploaded study material.
          </p>
        </div>
      </div>

      {/* Sources (30%) */}
      <div className="w-80 flex-shrink-0 bg-slate-50 overflow-y-auto">
        <div className="px-5 py-4 border-b border-slate-200 bg-white">
          <h3 className="text-sm font-semibold text-slate-800">Sources</h3>
          <p className="text-xs text-slate-400 mt-0.5">Referenced in the last response</p>
        </div>
        <div className="p-4 space-y-3">
          {SOURCES.map(source => (
            <div
              key={source.id}
              className={`bg-white border rounded-xl p-4 cursor-pointer transition-all ${
                activeSourceIds.includes(source.id) ? 'border-indigo-200 ring-1 ring-indigo-100' : 'border-slate-200 hover:border-slate-300'
              }`}
              onClick={() => setActiveSourceIds([source.id])}
            >
              <div className="flex items-start gap-2.5 mb-2">
                <sup className="text-indigo-600 font-bold text-xs mt-0.5">[{source.id}]</sup>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <FileText size={12} className="text-red-400 flex-shrink-0" />
                    <span className="text-xs font-medium text-slate-700 truncate">{source.document}</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">Page {source.page}</div>
                </div>
              </div>
              <p className="text-xs text-slate-500 italic leading-relaxed border-l-2 border-indigo-200 pl-3">
                {source.excerpt}
              </p>
              <button className="mt-2 text-xs text-indigo-600 hover:underline flex items-center gap-1">
                Open in document <ChevronRight size={11} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
