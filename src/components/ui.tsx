import React from 'react';
import type { MasteryLevel } from '../types';

export function MasteryBadge({ level, size = 'sm' }: { level: MasteryLevel; size?: 'sm' | 'md' }) {
  const labels: Record<MasteryLevel, string> = {
    mastered: 'Mastered',
    developing: 'Developing',
    weak: 'Weak',
    unassessed: 'Not Assessed',
  };
  const cls = size === 'sm'
    ? 'text-xs px-2 py-0.5 rounded-full font-medium'
    : 'text-sm px-3 py-1 rounded-full font-medium';
  return (
    <span className={`${cls} badge-${level}`}>{labels[level]}</span>
  );
}

export function MasteryDot({ level }: { level: MasteryLevel }) {
  const colors: Record<MasteryLevel, string> = {
    mastered: 'bg-green-500',
    developing: 'bg-amber-500',
    weak: 'bg-red-500',
    unassessed: 'bg-slate-300',
  };
  return <span className={`inline-block w-2 h-2 rounded-full ${colors[level]} flex-shrink-0`} />;
}

export function MasteryBar({ value, level, label }: { value: number; level: MasteryLevel; label: string }) {
  const colors: Record<MasteryLevel, string> = {
    mastered: 'bg-green-500',
    developing: 'bg-amber-400',
    weak: 'bg-red-400',
    unassessed: 'bg-slate-300',
  };
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-sm text-slate-600">{label}</span>
        <span className="text-sm font-semibold font-mono-data text-slate-800">{value}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${colors[level]}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: React.ReactNode;
  accent?: 'indigo' | 'green' | 'amber' | 'red' | 'slate';
  onClick?: () => void;
}

export function StatCard({ label, value, sub, icon, accent = 'slate', onClick }: StatCardProps) {
  const accentBg: Record<string, string> = {
    indigo: 'bg-indigo-50',
    green: 'bg-green-50',
    amber: 'bg-amber-50',
    red: 'bg-red-50',
    slate: 'bg-slate-50',
  };
  const accentIcon: Record<string, string> = {
    indigo: 'text-indigo-600',
    green: 'text-green-600',
    amber: 'text-amber-600',
    red: 'text-red-600',
    slate: 'text-slate-600',
  };
  return (
    <div
      className={`bg-white border border-slate-100 rounded-xl p-5 space-y-3 ${onClick ? 'cursor-pointer hover:border-slate-200 hover:shadow-sm transition-all' : ''}`}
      onClick={onClick}
    >
      {icon && (
        <div className={`w-9 h-9 rounded-lg ${accentBg[accent]} flex items-center justify-center ${accentIcon[accent]}`}>
          {icon}
        </div>
      )}
      <div>
        <div className="text-2xl font-bold text-slate-900 font-mono-data">{value}</div>
        <div className="text-sm text-slate-500 mt-0.5">{label}</div>
        {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
      </div>
    </div>
  );
}

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-8 text-center">
      <div className="w-14 h-14 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mb-4">
        {icon}
      </div>
      <h3 className="text-slate-800 font-semibold text-lg mb-1">{title}</h3>
      <p className="text-slate-500 text-sm max-w-xs">{description}</p>
      {action && (
        <button
          className="mt-5 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          onClick={action.onClick}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

export function Divider() {
  return <div className="border-t border-slate-100 my-6" />;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  disabled,
  className = '',
}: {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}) {
  const base = 'inline-flex items-center gap-2 font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';
  const variants = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700',
    secondary: 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50',
    ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-800',
    danger: 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100',
  };
  const sizes = {
    sm: 'text-sm px-3 py-1.5',
    md: 'text-sm px-4 py-2',
    lg: 'text-base px-5 py-2.5',
  };
  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export function Tag({ children, color = 'slate' }: { children: React.ReactNode; color?: 'indigo' | 'green' | 'amber' | 'red' | 'slate' }) {
  const colors: Record<string, string> = {
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-100',
    green: 'bg-green-50 text-green-700 border-green-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
    red: 'bg-red-50 text-red-700 border-red-100',
    slate: 'bg-slate-50 text-slate-600 border-slate-200',
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${colors[color]}`}>
      {children}
    </span>
  );
}
