import React from 'react';

export function Badge({ children, variant = 'default', size = 'sm' }) {
  const base = "inline-flex items-center font-medium rounded-md px-2 py-0.5 text-xs border";
  
  const variants = {
    // Severity
    CRITICAL: "bg-red-950/60 text-red-300 border-red-800",
    HIGH: "bg-orange-950/60 text-orange-300 border-orange-800",
    MEDIUM: "bg-amber-950/60 text-amber-300 border-amber-800",
    LOW: "bg-blue-950/60 text-blue-300 border-blue-800",
    NORMAL: "bg-slate-800 text-slate-300 border-slate-700",

    // Classification
    REGRESSION: "bg-rose-950/50 text-rose-300 border-rose-800",
    FLAKY_TEST: "bg-purple-950/50 text-purple-300 border-purple-800",
    INFRASTRUCTURE: "bg-amber-950/50 text-amber-300 border-amber-800",
    ENVIRONMENT: "bg-teal-950/50 text-teal-300 border-teal-800",
    DEPENDENCY: "bg-indigo-950/50 text-indigo-300 border-indigo-800",
    NETWORK: "bg-cyan-950/50 text-cyan-300 border-cyan-800",
    TIMEOUT: "bg-yellow-950/50 text-yellow-300 border-yellow-800",
    BUILD_FAILURE: "bg-red-950/50 text-red-300 border-red-800",
    TEST_DATA: "bg-pink-950/50 text-pink-300 border-pink-800",
    UNKNOWN: "bg-slate-800 text-slate-400 border-slate-700",

    // Status
    SUCCESS: "bg-emerald-950/60 text-emerald-300 border-emerald-800",
    FAILURE: "bg-rose-950/60 text-rose-300 border-rose-800",
    QUEUED: "bg-slate-800 text-slate-300 border-slate-700",
    IN_PROGRESS: "bg-sky-950/60 text-sky-300 border-sky-800",
    PENDING_APPROVAL: "bg-amber-950/60 text-amber-300 border-amber-800",
    APPROVED: "bg-emerald-950/60 text-emerald-300 border-emerald-800",
    EXECUTED: "bg-indigo-950/60 text-indigo-300 border-indigo-800",
    REJECTED: "bg-slate-800 text-slate-400 border-slate-700",

    // Roles
    ADMIN: "bg-rose-900/40 text-rose-200 border-rose-700",
    INVESTIGATOR: "bg-brand-900/40 text-brand-200 border-brand-700",
    DEVELOPER: "bg-sky-900/40 text-sky-200 border-sky-700",
    VIEWER: "bg-slate-800 text-slate-300 border-slate-700",

    // CI Providers
    github_actions: "bg-sky-950/60 text-sky-300 border-sky-800",
    jenkins: "bg-amber-950/60 text-amber-300 border-amber-800",

    default: "bg-slate-800 text-slate-300 border-slate-700"
  };

  const vClass = variants[variant] || variants.default;

  return (
    <span className={`${base} ${vClass}`}>
      {children}
    </span>
  );
}
