import React, { useState, useEffect } from 'react';
import {
  BookOpen, LayoutDashboard, FileText, Map, MessageCircle,
  CreditCard, HelpCircle, ClipboardCheck, BarChart2, Activity,
  Settings, ShieldCheck, ChevronLeft, ChevronRight, Bell,
  Search, User, Layers, LogOut, Command
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import type { View } from '../types';
import { SPACES, PROJECTS } from '../data/mockData';
import CommandPalette from './CommandPalette';

const PROJECT_NAV: { view: View; label: string; icon: React.ReactNode }[] = [
  { view: 'overview', label: 'Overview', icon: <LayoutDashboard size={16} /> },
  { view: 'documents', label: 'Documents', icon: <FileText size={16} /> },
  { view: 'structure', label: 'Structure', icon: <Map size={16} /> },
  { view: 'tutor', label: 'Tutor', icon: <MessageCircle size={16} /> },
  { view: 'flashcards', label: 'Flashcards', icon: <CreditCard size={16} /> },
  { view: 'quiz', label: 'Quiz', icon: <HelpCircle size={16} /> },
  { view: 'assessments', label: 'Assessments', icon: <ClipboardCheck size={16} /> },
  { view: 'dashboard', label: 'Dashboard', icon: <BarChart2 size={16} /> },
  { view: 'analytics', label: 'Analytics', icon: <Layers size={16} /> },
  { view: 'activity', label: 'Activity', icon: <Activity size={16} /> },
  { view: 'settings', label: 'Settings', icon: <Settings size={16} /> },
];

const PROJECT_VIEWS: View[] = PROJECT_NAV.map(n => n.view);

export default function Layout({ children }: { children: React.ReactNode }) {
  const { state, navigate, toggleSidebar, setCommandOpen, logout } = useApp();
  const { view, sidebarCollapsed, commandOpen, selectedSpaceId, selectedProjectId } = state;

  const space = SPACES.find(s => s.id === selectedSpaceId);
  const project = PROJECTS.find(p => p.id === selectedProjectId);

  const isProjectView = PROJECT_VIEWS.includes(view);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandOpen(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const topLevelViews: { view: View; label: string }[] = [
    { view: 'spaces', label: 'Spaces' },
    { view: 'projects', label: space?.name ?? 'Projects' },
  ];

  const breadcrumb = isProjectView
    ? [space?.name, project?.name, PROJECT_NAV.find(n => n.view === view)?.label]
        .filter(Boolean)
        .join(' / ')
    : view === 'projects'
    ? `${space?.name ?? 'Space'} / Projects`
    : 'Spaces';

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`flex flex-col bg-white border-r border-slate-200 transition-all duration-200 flex-shrink-0 ${
          sidebarCollapsed ? 'w-16' : 'w-60'
        }`}
      >
        {/* Logo */}
        <div className={`flex items-center h-14 px-4 border-b border-slate-100 flex-shrink-0 ${sidebarCollapsed ? 'justify-center' : 'gap-2.5'}`}>
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
            <BookOpen size={14} className="text-white" />
          </div>
          {!sidebarCollapsed && (
            <span className="font-semibold text-slate-900 text-sm">Study Companion</span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2">
          {/* Top-level */}
          {!isProjectView && (
            <div className="space-y-0.5 mb-3">
              {topLevelViews.map(item => (
                <div
                  key={item.view}
                  className={`sidebar-item ${view === item.view ? 'active' : ''}`}
                  onClick={() => navigate(item.view)}
                  title={sidebarCollapsed ? item.label : undefined}
                >
                  <Layers size={16} className="flex-shrink-0" />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </div>
              ))}
            </div>
          )}

          {/* Project nav */}
          {isProjectView && (
            <>
              {!sidebarCollapsed && (
                <div className="px-3 pt-1 pb-2">
                  <button
                    className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors"
                    onClick={() => navigate('projects')}
                  >
                    <ChevronLeft size={12} />
                    <span>{space?.name}</span>
                  </button>
                  <div className="mt-2 text-xs font-semibold text-slate-400 uppercase tracking-widest px-0.5">
                    {project?.name}
                  </div>
                </div>
              )}
              <div className="space-y-0.5">
                {PROJECT_NAV.map(item => (
                  <div
                    key={item.view}
                    className={`sidebar-item ${view === item.view ? 'active' : ''}`}
                    onClick={() => navigate(item.view)}
                    title={sidebarCollapsed ? item.label : undefined}
                  >
                    <span className="flex-shrink-0">{item.icon}</span>
                    {!sidebarCollapsed && <span>{item.label}</span>}
                  </div>
                ))}
              </div>
            </>
          )}

          {!sidebarCollapsed && (
            <div className="mt-4 px-1">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest px-2 mb-1">Workspace</div>
              <div
                className={`sidebar-item ${view === 'admin' ? 'active' : ''}`}
                onClick={() => navigate('admin')}
              >
                <ShieldCheck size={16} className="flex-shrink-0" />
                {!sidebarCollapsed && <span>Admin</span>}
              </div>
            </div>
          )}
        </nav>

        {/* Bottom */}
        <div className={`border-t border-slate-100 p-2 space-y-0.5`}>
          <div
            className="sidebar-item"
            onClick={() => setCommandOpen(true)}
            title={sidebarCollapsed ? 'Command' : undefined}
          >
            <Command size={16} className="flex-shrink-0" />
            {!sidebarCollapsed && <span>Command</span>}
          </div>
          <div className="sidebar-item" onClick={logout} title={sidebarCollapsed ? 'Sign out' : undefined}>
            <LogOut size={16} className="flex-shrink-0" />
            {!sidebarCollapsed && <span>Sign out</span>}
          </div>
          <button
            className="sidebar-item w-full"
            onClick={toggleSidebar}
            title={sidebarCollapsed ? 'Expand' : 'Collapse'}
          >
            {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            {!sidebarCollapsed && <span className="text-xs">Collapse</span>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top nav */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center px-6 gap-4 flex-shrink-0">
          <div className="flex-1 text-sm text-slate-500 font-medium truncate">{breadcrumb}</div>
          <button
            className="flex items-center gap-2 text-sm text-slate-400 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 hover:bg-slate-100 transition-colors"
            onClick={() => setCommandOpen(true)}
          >
            <Search size={14} />
            <span>Search</span>
            <kbd className="ml-1 text-xs text-slate-400 font-mono-data">⌘K</kbd>
          </button>
          <NotifBell />
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 text-xs font-semibold cursor-pointer">
            AR
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>

      {commandOpen && <CommandPalette />}
    </div>
  );
}

function NotifBell() {
  const [open, setOpen] = useState(false);
  const notifs = [
    { id: 1, text: '8 flashcards are due for review.', time: 'Now' },
    { id: 2, text: 'Confidence/correctness mismatch increased for Lasso Regression.', time: '1h ago' },
    { id: 3, text: 'Knowledge map generated from Ensemble Methods.pdf.', time: '2h ago' },
    { id: 4, text: 'Applied Mastery improved — Linear Regression now at 88%.', time: 'Yesterday' },
  ];
  return (
    <div className="relative">
      <button
        className="relative w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <Bell size={16} className="text-slate-500" />
        <span className="absolute top-1 right-1 w-2 h-2 bg-indigo-600 rounded-full" />
      </button>
      {open && (
        <div className="absolute right-0 top-10 w-80 bg-white border border-slate-200 rounded-xl shadow-lg z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-800">Notifications</span>
            <span className="text-xs text-indigo-600 cursor-pointer hover:underline">Mark all read</span>
          </div>
          {notifs.map(n => (
            <div key={n.id} className="px-4 py-3 hover:bg-slate-50 cursor-pointer border-b border-slate-50 last:border-0">
              <p className="text-sm text-slate-700">{n.text}</p>
              <p className="text-xs text-slate-400 mt-0.5">{n.time}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
