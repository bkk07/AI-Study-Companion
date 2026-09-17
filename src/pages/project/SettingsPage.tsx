import React, { useState } from 'react';
import { SectionHeader, Button, Divider } from '../../components/ui';
import { User, Brain, Bell, Palette, Database, Settings, AlertTriangle } from 'lucide-react';

type SettingsSection = 'profile' | 'learning' | 'ai' | 'notifications' | 'appearance' | 'data' | 'project' | 'danger';

const SECTIONS: { key: SettingsSection; label: string; icon: React.ReactNode }[] = [
  { key: 'profile', label: 'Profile', icon: <User size={16} /> },
  { key: 'learning', label: 'Learning Preferences', icon: <Brain size={16} /> },
  { key: 'ai', label: 'AI Preferences', icon: <Brain size={16} /> },
  { key: 'notifications', label: 'Notifications', icon: <Bell size={16} /> },
  { key: 'appearance', label: 'Appearance', icon: <Palette size={16} /> },
  { key: 'data', label: 'Data Management', icon: <Database size={16} /> },
  { key: 'project', label: 'Project Settings', icon: <Settings size={16} /> },
  { key: 'danger', label: 'Danger Zone', icon: <AlertTriangle size={16} /> },
];

function Toggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button
      className={`w-10 h-5.5 rounded-full transition-colors relative flex-shrink-0 ${on ? 'bg-indigo-600' : 'bg-slate-200'}`}
      onClick={onToggle}
      style={{ height: 22, width: 40 }}
    >
      <div className={`absolute top-0.5 w-4.5 h-4.5 bg-white rounded-full shadow transition-transform ${on ? 'translate-x-5' : 'translate-x-0.5'}`}
        style={{ height: 18, width: 18, transition: 'transform 0.15s' }} />
    </button>
  );
}

function SettingRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-slate-100 last:border-0">
      <div className="flex-1 pr-8">
        <div className="text-sm font-medium text-slate-800">{label}</div>
        {description && <div className="text-xs text-slate-400 mt-0.5">{description}</div>}
      </div>
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const [section, setSection] = useState<SettingsSection>('profile');
  const [toggles, setToggles] = useState({
    adaptiveQuiz: true,
    confidenceTracking: true,
    mismatchAlerts: true,
    flashcardNotifs: true,
    progressSummary: false,
    darkMode: false,
    compactMode: false,
    groundedAI: true,
    citationMode: true,
    quickActions: true,
  });

  const toggle = (key: keyof typeof toggles) => setToggles(t => ({ ...t, [key]: !t[key] }));

  const renderSection = () => {
    switch (section) {
      case 'profile':
        return (
          <div className="space-y-5">
            <div className="flex items-center gap-5 mb-6">
              <div className="w-16 h-16 rounded-2xl bg-indigo-100 text-indigo-700 flex items-center justify-center text-xl font-bold">AR</div>
              <div>
                <div className="text-base font-semibold text-slate-900">Arjun Reddy</div>
                <div className="text-sm text-slate-500">arjun.reddy@nitk.edu</div>
                <button className="text-xs text-indigo-600 hover:underline mt-1">Change avatar</button>
              </div>
            </div>
            {[
              { label: 'Full name', value: 'Arjun Reddy', type: 'text' },
              { label: 'Email address', value: 'arjun.reddy@nitk.edu', type: 'email' },
              { label: 'University / Institution', value: 'NITK Surathkal', type: 'text' },
              { label: 'Program', value: 'B.Tech Computer Science', type: 'text' },
            ].map(f => (
              <div key={f.label}>
                <label className="text-sm font-medium text-slate-700 block mb-1.5">{f.label}</label>
                <input
                  type={f.type}
                  defaultValue={f.value}
                  className="w-full max-w-sm px-3 py-2 border border-slate-200 rounded-lg text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-50 transition"
                />
              </div>
            ))}
            <Button variant="primary">Save changes</Button>
          </div>
        );

      case 'learning':
        return (
          <div>
            <SettingRow label="Adaptive quiz difficulty" description="Automatically adjust question difficulty based on your mastery evidence">
              <Toggle on={toggles.adaptiveQuiz} onToggle={() => toggle('adaptiveQuiz')} />
            </SettingRow>
            <SettingRow label="Confidence tracking" description="Collect confidence ratings alongside quiz answers to detect mismatches">
              <Toggle on={toggles.confidenceTracking} onToggle={() => toggle('confidenceTracking')} />
            </SettingRow>
            <SettingRow label="Mismatch alerts" description="Alert me when confidence and correctness are significantly misaligned">
              <Toggle on={toggles.mismatchAlerts} onToggle={() => toggle('mismatchAlerts')} />
            </SettingRow>
            <SettingRow label="Daily study goal">
              <select className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 text-slate-700 outline-none">
                <option>30 minutes</option>
                <option>60 minutes</option>
                <option>90 minutes</option>
                <option>2 hours</option>
              </select>
            </SettingRow>
            <SettingRow label="New flashcards per session">
              <select className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 text-slate-700 outline-none">
                <option>5</option>
                <option>10</option>
                <option>15</option>
                <option>20</option>
              </select>
            </SettingRow>
          </div>
        );

      case 'ai':
        return (
          <div>
            <SettingRow label="Grounded-only responses" description="AI tutor will only respond based on your uploaded study material">
              <Toggle on={toggles.groundedAI} onToggle={() => toggle('groundedAI')} />
            </SettingRow>
            <SettingRow label="Show source citations" description="Display document and page references in AI responses">
              <Toggle on={toggles.citationMode} onToggle={() => toggle('citationMode')} />
            </SettingRow>
            <SettingRow label="Quick action buttons" description="Show suggested follow-up actions after AI responses">
              <Toggle on={toggles.quickActions} onToggle={() => toggle('quickActions')} />
            </SettingRow>
            <SettingRow label="Response detail level">
              <select className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 text-slate-700 outline-none">
                <option>Concise</option>
                <option>Standard</option>
                <option>Detailed</option>
              </select>
            </SettingRow>
          </div>
        );

      case 'notifications':
        return (
          <div>
            <SettingRow label="Flashcard review reminders" description="Notify when cards are due for spaced repetition">
              <Toggle on={toggles.flashcardNotifs} onToggle={() => toggle('flashcardNotifs')} />
            </SettingRow>
            <SettingRow label="Mismatch detection alerts" description="Alert when confidence/correctness mismatch worsens">
              <Toggle on={toggles.mismatchAlerts} onToggle={() => toggle('mismatchAlerts')} />
            </SettingRow>
            <SettingRow label="Weekly progress summary" description="Receive a weekly digest of your learning progress">
              <Toggle on={toggles.progressSummary} onToggle={() => toggle('progressSummary')} />
            </SettingRow>
          </div>
        );

      case 'appearance':
        return (
          <div>
            <SettingRow label="Dark mode">
              <Toggle on={toggles.darkMode} onToggle={() => toggle('darkMode')} />
            </SettingRow>
            <SettingRow label="Compact sidebar">
              <Toggle on={toggles.compactMode} onToggle={() => toggle('compactMode')} />
            </SettingRow>
            <SettingRow label="Accent color">
              <div className="flex gap-2">
                {['#4f46e5', '#0891b2', '#7c3aed', '#0d9488', '#c2410c'].map(c => (
                  <div key={c} className="w-6 h-6 rounded-full cursor-pointer ring-2 ring-white ring-offset-1 hover:scale-110 transition-transform" style={{ backgroundColor: c }} />
                ))}
              </div>
            </SettingRow>
          </div>
        );

      case 'data':
        return (
          <div className="space-y-4">
            <SettingRow label="Export learning data" description="Download all your mastery evidence, quiz attempts, and flashcard history as JSON">
              <Button variant="secondary" size="sm">Export</Button>
            </SettingRow>
            <SettingRow label="Export flashcard deck" description="Export flashcards as a CSV or Anki-compatible format">
              <Button variant="secondary" size="sm">Export deck</Button>
            </SettingRow>
            <SettingRow label="Clear quiz history" description="Remove all quiz attempt records (mastery will reset)">
              <Button variant="danger" size="sm">Clear</Button>
            </SettingRow>
          </div>
        );

      case 'danger':
        return (
          <div className="space-y-4">
            <div className="bg-red-50 border border-red-200 rounded-xl p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle size={18} className="text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-sm font-semibold text-red-800 mb-1">Delete Project</div>
                  <p className="text-xs text-red-600 mb-3">This will permanently delete Machine Learning and all associated documents, flashcards, quiz history, and mastery data. This cannot be undone.</p>
                  <Button variant="danger" size="sm">Delete this project</Button>
                </div>
              </div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle size={18} className="text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-sm font-semibold text-red-800 mb-1">Delete Account</div>
                  <p className="text-xs text-red-600 mb-3">Permanently delete your account and all data. This action is irreversible.</p>
                  <Button variant="danger" size="sm">Delete account</Button>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return <div className="text-sm text-slate-400">Settings for {section} coming soon.</div>;
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-8 py-10">
      <SectionHeader title="Settings" />
      <div className="flex gap-8">
        {/* Section nav */}
        <aside className="w-48 flex-shrink-0">
          <nav className="space-y-0.5">
            {SECTIONS.map(s => (
              <button
                key={s.key}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-left transition-colors ${
                  section === s.key ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'
                }`}
                onClick={() => setSection(s.key)}
              >
                <span className="flex-shrink-0">{s.icon}</span>
                <span>{s.label}</span>
              </button>
            ))}
          </nav>
        </aside>

        {/* Content */}
        <div className="flex-1 min-w-0 bg-white border border-slate-200 rounded-xl p-6">
          <h3 className="text-base font-semibold text-slate-900 mb-5">
            {SECTIONS.find(s => s.key === section)?.label}
          </h3>
          {renderSection()}
        </div>
      </div>
    </div>
  );
}
