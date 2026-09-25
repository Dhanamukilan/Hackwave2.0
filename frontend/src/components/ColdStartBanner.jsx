import React from 'react';
import { Info, Database, CheckCircle2 } from 'lucide-react';

export function ColdStartBanner({ metrics }) {
  if (!metrics) return null;

  const isSynthetic = metrics.provenance === 'synthetic_benchmark';
  const realCount = metrics.real_samples_count || 0;
  const threshold = metrics.min_samples_threshold || 200;
  const progressPercent = Math.min(100, Math.round((realCount / threshold) * 100));

  return (
    <div className={`rounded-xl p-4 border transition-all mb-6 ${
      isSynthetic 
        ? 'bg-amber-950/20 border-amber-800/60 text-amber-200'
        : 'bg-emerald-950/20 border-emerald-800/60 text-emerald-200'
    }`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          {isSynthetic ? (
            <Info className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm">
                Evaluation Provenance: {metrics.provenance_label}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-900 border border-slate-700 text-slate-300 font-mono">
                {isSynthetic ? 'Rule §8 Active' : 'Production Real Data'}
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1">
              {isSynthetic
                ? `System is in cold-start baseline evaluation. Metrics are strictly computed from labeled synthetic benchmark scenarios. Once ≥ ${threshold} real runs exist (currently ${realCount}), evaluation switches automatically to real-data performance.`
                : `Evaluation is computed against ${realCount} real production pipeline runs and developer verification feedback.`}
            </p>
          </div>
        </div>

        <div className="text-right shrink-0 ml-4 hidden md:block">
          <div className="text-xs font-mono text-slate-300">
            {realCount} / {threshold} runs
          </div>
          <div className="w-32 bg-slate-900 h-2 rounded-full overflow-hidden mt-1 border border-slate-700">
            <div
              className={`h-full transition-all duration-500 ${isSynthetic ? 'bg-amber-500' : 'bg-emerald-500'}`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
