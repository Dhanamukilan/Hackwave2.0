import React from 'react';
import { Activity, ShieldCheck, UserCheck, LogOut, Terminal, GitCommit } from 'lucide-react';
import { Badge } from './Badge';

export function Navbar({ user, onLogout, onOpenLogin }) {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-brand-500/20">
          AG
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold tracking-tight text-white">AG004</span>
            <span className="text-xs bg-brand-950 text-brand-300 border border-brand-800 px-1.5 py-0.5 rounded font-mono">v1.0</span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">CI/CD Failure Triage & Flaky-Test Intelligence</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-xs text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Local Intelligence Engine Online</span>
        </div>

        {user ? (
          <div className="flex items-center gap-3 pl-2 border-l border-slate-800">
            <div className="text-right hidden sm:block">
              <div className="text-sm font-medium text-slate-200">{user.username}</div>
              <div className="text-xs text-slate-400">{user.email}</div>
            </div>
            <Badge variant={user.role}>{user.role}</Badge>
            <button
              onClick={onLogout}
              className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenLogin}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-brand-600 hover:bg-brand-500 text-white transition shadow-sm"
          >
            Sign In
          </button>
        )}
      </div>
    </header>
  );
}
