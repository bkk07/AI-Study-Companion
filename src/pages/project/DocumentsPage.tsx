import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, Loader2, Clock, AlertCircle, Trash2, Eye, RefreshCw, ChevronRight } from 'lucide-react';
import { DOCUMENTS } from '../../data/mockData';
import { SectionHeader, EmptyState } from '../../components/ui';

const PIPELINE_STEPS = ['Upload', 'Extracting Text', 'Chunking', 'Generating Embeddings', 'Building Knowledge Map', 'Ready'];

function ProcessingPipeline({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-2 mt-3">
      {PIPELINE_STEPS.map((s, i) => (
        <React.Fragment key={s}>
          <div className="flex flex-col items-center gap-1">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
              i < step ? 'bg-green-100 text-green-600' : i === step ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-400'
            }`}>
              {i < step ? <CheckCircle size={12} /> : i === step ? <Loader2 size={12} className="animate-spin" /> : i + 1}
            </div>
            <span className={`text-xs whitespace-nowrap ${i <= step ? 'text-slate-600' : 'text-slate-400'}`}>{s}</span>
          </div>
          {i < PIPELINE_STEPS.length - 1 && (
            <div className={`flex-1 h-px ${i < step ? 'bg-green-300' : 'bg-slate-200'}`} style={{ minWidth: 12 }} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export default function DocumentsPage() {
  const [tab, setTab] = useState<'upload' | 'library'>('library');
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [pipelineStep, setPipelineStep] = useState(0);
  const [uploadedFile, setUploadedFile] = useState<{ name: string; size: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const simulateUpload = (name: string, size: string) => {
    setUploadedFile({ name, size });
    setUploading(true);
    setPipelineStep(0);
    const advance = (step: number) => {
      if (step <= 5) {
        setPipelineStep(step);
        setTimeout(() => advance(step + 1), 800);
      } else {
        setUploading(false);
      }
    };
    setTimeout(() => advance(1), 400);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) simulateUpload(file.name, `${(file.size / 1024 / 1024).toFixed(1)} MB`);
  };

  const statusBadge = (status: string) => {
    const cfg: Record<string, { text: string; cls: string }> = {
      ready: { text: 'Ready', cls: 'badge-mastered' },
      processing: { text: 'Processing', cls: 'badge-developing' },
      queued: { text: 'Queued', cls: 'badge-unassessed' },
      failed: { text: 'Failed', cls: 'badge-weak' },
    };
    const c = cfg[status] ?? cfg.queued;
    return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${c.cls}`}>{c.text}</span>;
  };

  return (
    <div className="max-w-5xl mx-auto px-8 py-10">
      <SectionHeader title="Documents" subtitle="Upload and manage your study material" />

      <div className="flex gap-1 mb-6 bg-slate-100 p-1 rounded-lg w-fit">
        {(['library', 'upload'] as const).map(t => (
          <button
            key={t}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${tab === t ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'upload' && (
        <div className="space-y-6">
          <div
            className={`border-2 border-dashed rounded-xl flex flex-col items-center justify-center py-20 transition-colors cursor-pointer ${
              dragging ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 hover:border-slate-300 bg-white'
            }`}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
          >
            <div className="w-14 h-14 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center mb-4">
              <Upload size={22} className="text-slate-400" />
            </div>
            <p className="text-sm font-medium text-slate-700">Drop your study material here</p>
            <p className="text-xs text-slate-400 mt-1">or click to browse — PDF files supported</p>
            <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={e => {
              const f = e.target.files?.[0];
              if (f) simulateUpload(f.name, `${(f.size / 1024 / 1024).toFixed(1)} MB`);
            }} />
          </div>

          {uploadedFile && (
            <div className="bg-white border border-slate-200 rounded-xl p-6">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-red-50 border border-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText size={18} className="text-red-500" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-800">{uploadedFile.name}</span>
                    {uploading
                      ? <span className="text-xs text-indigo-600 font-medium flex items-center gap-1"><Loader2 size={12} className="animate-spin" />Processing…</span>
                      : <span className="text-xs text-green-600 font-medium flex items-center gap-1"><CheckCircle size={12} />Ready</span>
                    }
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">{uploadedFile.size}</div>
                  <div className="overflow-x-auto mt-4 pb-2">
                    <ProcessingPipeline step={pipelineStep} />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'library' && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Document</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Pages</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Chunks</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Uploaded</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {DOCUMENTS.map((doc, i) => (
                <tr key={doc.id} className={`border-b border-slate-50 hover:bg-slate-50 transition-colors ${i === DOCUMENTS.length - 1 ? 'border-0' : ''}`}>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-red-50 border border-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <FileText size={14} className="text-red-500" />
                      </div>
                      <div>
                        <div className="font-medium text-slate-800">{doc.name}</div>
                        {doc.status === 'ready' && (
                          <div className="text-xs text-slate-400 mt-0.5">{doc.conceptsDetected} concepts detected</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 font-mono-data text-slate-600">{doc.pages}</td>
                  <td className="px-4 py-4 font-mono-data text-slate-600">{doc.chunks || '—'}</td>
                  <td className="px-4 py-4">{statusBadge(doc.status)}</td>
                  <td className="px-4 py-4 text-slate-500 text-xs">{doc.uploadedAt}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 justify-end">
                      {doc.status === 'ready' && (
                        <button className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors" title="View">
                          <Eye size={14} />
                        </button>
                      )}
                      {doc.status === 'failed' && (
                        <button className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors" title="Retry">
                          <RefreshCw size={14} />
                        </button>
                      )}
                      <button className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors" title="Delete">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
