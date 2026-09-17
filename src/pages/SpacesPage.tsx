import React, { useState } from 'react';
import { Plus, MoreHorizontal, FolderOpen, Clock, Layers } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { SPACES } from '../data/mockData';
import { EmptyState } from '../components/ui';

export default function SpacesPage() {
  const { navigate, setSpaceId } = useApp();
  const [spaces, setSpaces] = useState(SPACES);

  const openSpace = (spaceId: string) => {
    setSpaceId(spaceId);
    navigate('projects');
  };

  return (
    <div className="max-w-4xl mx-auto px-8 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Your Spaces</h1>
          <p className="text-slate-500 text-sm mt-0.5">Organize your learning into subject areas</p>
        </div>
        <button className="flex items-center gap-2 bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
          <Plus size={15} />
          New Space
        </button>
      </div>

      {spaces.length === 0 ? (
        <EmptyState
          icon={<Layers size={24} />}
          title="No spaces yet"
          description="Create your first space to organize your learning into subject areas."
          action={{ label: 'Create a space', onClick: () => {} }}
        />
      ) : (
        <div className="grid gap-4">
          {spaces.map(space => (
            <div
              key={space.id}
              className="bg-white border border-slate-200 rounded-xl p-6 hover:border-slate-300 hover:shadow-sm transition-all cursor-pointer group"
              onClick={() => openSpace(space.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div
                    className="w-10 h-10 rounded-xl flex-shrink-0 flex items-center justify-center"
                    style={{ backgroundColor: space.color + '18', color: space.color }}
                  >
                    <FolderOpen size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-slate-900 group-hover:text-indigo-700 transition-colors">
                      {space.name}
                    </h3>
                    <p className="text-slate-500 text-sm mt-0.5">{space.description}</p>
                    <div className="flex items-center gap-4 mt-3 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Layers size={12} />
                        {space.projectCount} projects
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={12} />
                        {space.lastActivity}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    className="px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
                    onClick={e => { e.stopPropagation(); openSpace(space.id); }}
                  >
                    Open
                  </button>
                  <button
                    className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
                    onClick={e => e.stopPropagation()}
                  >
                    <MoreHorizontal size={15} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
