import React from 'react';
import { ShieldCheck, Users, FolderOpen, FileText, HelpCircle, CreditCard, MessageCircle, MoreHorizontal } from 'lucide-react';

const USERS = [
  { name: 'Arjun Reddy', email: 'arjun.reddy@nitk.edu', joined: 'Aug 12, 2026', projects: 4, activity: 'Today', isAdmin: true },
  { name: 'Priya Sharma', email: 'priya.s@iit.edu', joined: 'Aug 19, 2026', projects: 3, activity: 'Yesterday', isAdmin: false },
  { name: 'Rohan Gupta', email: 'rohan.g@bits.ac.in', joined: 'Sep 1, 2026', projects: 2, activity: '3 days ago', isAdmin: false },
  { name: 'Ananya Patel', email: 'ananya.p@vit.edu', joined: 'Sep 5, 2026', projects: 1, activity: '5 days ago', isAdmin: false },
  { name: 'Karthik Rajan', email: 'karthik.r@rec.edu', joined: 'Sep 10, 2026', projects: 2, activity: '2 days ago', isAdmin: false },
];

export default function AdminPage() {
  return (
    <div className="max-w-5xl mx-auto px-8 py-10">
      {/* Admin badge */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center">
          <ShieldCheck size={20} className="text-white" />
        </div>
        <div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Admin</div>
          <h1 className="text-xl font-semibold text-slate-900">System Overview</h1>
        </div>
      </div>

      {/* System stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-10">
        {[
          { label: 'Users', value: 5, icon: <Users size={16} /> },
          { label: 'Projects', value: 14, icon: <FolderOpen size={16} /> },
          { label: 'Documents', value: 47, icon: <FileText size={16} /> },
          { label: 'Quiz Attempts', value: 312, icon: <HelpCircle size={16} /> },
          { label: 'Flashcard Reviews', value: 1840, icon: <CreditCard size={16} /> },
          { label: 'Tutor Questions', value: 198, icon: <MessageCircle size={16} /> },
        ].map(s => (
          <div key={s.label} className="bg-white border border-slate-200 rounded-xl px-4 py-4">
            <div className="w-8 h-8 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center text-slate-600 mb-2">
              {s.icon}
            </div>
            <div className="text-2xl font-bold font-mono-data text-slate-900">{s.value.toLocaleString()}</div>
            <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Users table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800">Users</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Name</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Email</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Joined</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Projects</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Activity</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Role</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            {USERS.map((user, i) => (
              <tr key={user.email} className={`border-b border-slate-50 hover:bg-slate-50 transition-colors ${i === USERS.length - 1 ? 'border-0' : ''}`}>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold flex items-center justify-center flex-shrink-0">
                      {user.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <span className="font-medium text-slate-800">{user.name}</span>
                  </div>
                </td>
                <td className="px-4 py-4 text-slate-500">{user.email}</td>
                <td className="px-4 py-4 text-slate-500 text-xs">{user.joined}</td>
                <td className="px-4 py-4 font-mono-data text-slate-600">{user.projects}</td>
                <td className="px-4 py-4 text-slate-500 text-xs">{user.activity}</td>
                <td className="px-4 py-4">
                  {user.isAdmin ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-900 text-white font-medium">Admin</span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">Student</span>
                  )}
                </td>
                <td className="px-6 py-4 text-right">
                  <button className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors">
                    <MoreHorizontal size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
