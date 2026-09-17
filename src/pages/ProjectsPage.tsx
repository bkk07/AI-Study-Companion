import React from 'react';
import { Plus, FileText, Map, Brain, Clock, ChevronRight } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { PROJECTS, SPACES } from '../data/mockData';
import { EmptyState, MasteryBar } from '../components/ui';
import type { MasteryLevel } from '../types';

function getMasteryLevel(v: number | null): MasteryLevel {
  if (v === null) return 'unassessed';
  if (v >= 80) return 'mastered';
  if (v >= 55) return 'developing';
  return 'weak';
}

export default function ProjectsPage() {
  const { navigate, setProjectId, state } = useApp();
  const space = SPACES.find(s => s.id === state.selectedSpaceId);
  const projects = PROJECTS.filter(p => p.spaceId === state.selectedSpaceId);

  const open = (id: string) => {
    setProjectId(id);
    navigate('overview');
  };

  return (
    <div className="max-w-5xl mx-auto px-8 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">{space?.name}</div>
          <h1 className="text-2xl font-semibold text-slate-900">Projects</h1>
          <p className="text-slate-500 text-sm mt-0.5">Each project is a focused learning workspace for a subject</p>
        </div>
        <button className="flex items-center gap-2 bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
          <Plus size={15} />
          New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <EmptyState
          icon={<Brain size={24} />}
          title="No projects yet"
          description="Create a project to start uploading your study material and building your knowledge map."
          action={{ label: 'Create a project', onClick: () => {} }}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {projects.map(project => (
            <div
              key={project.id}
              className="bg-white border border-slate-200 rounded-xl p-6 hover:border-slate-300 hover:shadow-sm transition-all cursor-pointer group"
              onClick={() => open(project.id)}
            >
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-base font-semibold text-slate-900 group-hover:text-indigo-700 transition-colors">
                  {project.name}
                </h3>
                <ChevronRight size={16} className="text-slate-300 group-hover:text-indigo-400 transition-colors flex-shrink-0 mt-0.5" />
              </div>
              <p className="text-slate-500 text-sm mb-5 line-clamp-2">{project.description}</p>

              <div className="flex gap-4 mb-5 text-xs text-slate-500">
                <span className="flex items-center gap-1.5"><FileText size={12} />{project.documentCount} docs</span>
                <span className="flex items-center gap-1.5"><Map size={12} />{project.topicCount} topics</span>
                <span className="flex items-center gap-1.5"><Brain size={12} />{project.conceptCount} concepts</span>
              </div>

              <div className="space-y-2.5 border-t border-slate-100 pt-4">
                {project.mcqMastery !== null ? (
                  <>
                    <MasteryBar value={project.mcqMastery} level={getMasteryLevel(project.mcqMastery)} label="MCQ Mastery" />
                    <MasteryBar value={project.appliedMastery!} level={getMasteryLevel(project.appliedMastery)} label="Applied Mastery" />
                  </>
                ) : (
                  <div className="text-xs text-slate-400 flex items-center gap-1.5">
                    <div className="w-2 h-2 bg-slate-200 rounded-full" />
                    Not assessed yet
                  </div>
                )}
              </div>

              <div className="mt-3 flex items-center gap-1 text-xs text-slate-400">
                <Clock size={11} />
                {project.lastActivity}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
