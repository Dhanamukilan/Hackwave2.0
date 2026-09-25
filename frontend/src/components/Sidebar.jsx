import React from 'react';
import {
  LayoutDashboard,
  GitBranch,
  AlertTriangle,
  FileSearch,
  Settings,
  Shield,
  Sparkles,
  Layers
} from 'lucide-react';

export function Sidebar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'pipelines', label: 'Pipelines & Builds', icon: GitBranch },
    { id: 'failures', label: 'Failure Triage', icon: AlertTriangle },
    { id: 'rca', label: 'RCA & Remediations', icon: FileSearch },
    { id: 'settings', label: 'Settings & RBAC', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/50 flex flex-col justify-between p-4 shrink-0">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs space-y-2">
        <div className="flex items-center gap-2 font-medium text-slate-200">
          <Sparkles className="w-4 h-4 text-brand-400" />
          <span>Multi-Agent Engine</span>
        </div>
        <p className="text-slate-400 text-[11px] leading-relaxed">
          Log &bull; History &bull; Git &bull; Component &bull; Evidence &bull; RCA (H1..H7) &bull; Remediation
        </p>
        <div className="pt-1 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
          <span>Vector Store</span>
          <span className="font-mono text-emerald-400">Qdrant Active</span>
        </div>
      </div>
    </aside>
  );
}
