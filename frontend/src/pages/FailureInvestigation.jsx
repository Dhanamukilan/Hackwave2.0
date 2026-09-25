import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Search,
  Sparkles,
  Layers,
  Fingerprint as FingerprintIcon,
  ShieldAlert,
  ArrowRight,
  Code2,
  Database,
  History,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { api } from '../services/api';
import { Badge } from '../components/Badge';

export function FailureInvestigation({ selectedFailureId, onNavigateToRCA }) {
  const [failures, setFailures] = useState([]);
  const [currentFailure, setCurrentFailure] = useState(null);
  const [fingerprints, setFingerprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [activeView, setActiveView] = useState('normalized'); // normalized or raw

  const loadFailures = async () => {
    setLoading(true);
    try {
      const [fList, fpList] = await Promise.all([
        api.getFailures('', '', 50),
        api.getFingerprints(15),
      ]);
      setFailures(fList);
      setFingerprints(fpList);

      if (selectedFailureId) {
        const found = fList.find((f) => f.id === selectedFailureId);
        setCurrentFailure(found || fList[0] || null);
      } else if (fList.length > 0) {
        setCurrentFailure(fList[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFailures();
  }, [selectedFailureId]);

  const handleLaunchInvestigation = async () => {
    if (!currentFailure) return;
    setIsInvestigating(true);
    try {
      const inv = await api.triggerInvestigation(currentFailure.id);
      if (onNavigateToRCA) {
        onNavigateToRCA(inv.id);
      }
    } catch (e) {
      alert(e.message || 'Investigation workflow failed');
    } finally {
      setIsInvestigating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Failure Triage & Deep Inspection</h1>
          <p className="text-sm text-slate-400">Log normalization, error fingerprinting, and semantic vector similarity</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left column: Failure selection list (4 cols) */}
        <div className="lg:col-span-4 rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="font-semibold text-xs text-slate-300 uppercase tracking-wider">
              Failures ({failures.length})
            </span>
          </div>

          <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
            {failures.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">No failures found.</p>
            ) : (
              failures.map((f) => {
                const isSelected = currentFailure && currentFailure.id === f.id;
                return (
                  <div
                    key={f.id}
                    onClick={() => setCurrentFailure(f)}
                    className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-brand-950/40 border-brand-500 shadow-md shadow-brand-500/10'
                        : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <span className="font-semibold text-xs text-slate-200 line-clamp-1">{f.error_type}</span>
                      <div className="flex items-center gap-1">
                        <Badge variant={f.ci_provider || 'github_actions'}>{f.ci_provider === 'jenkins' ? 'Jenkins' : 'GitHub'}</Badge>
                        <Badge variant={f.severity}>{f.severity}</Badge>
                      </div>
                    </div>
                    <div className="text-[11px] text-slate-400 line-clamp-2 mb-2 font-mono">
                      {f.normalized_message}
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1.5 border-t border-slate-800">
                      <Badge variant={f.classification}>{f.classification}</Badge>
                      <span className="font-mono text-purple-300">Flaky: {Math.round(f.flakiness_score * 100)}%</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right column: Detailed Inspection View (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {currentFailure ? (
            <>
              {/* Header Card */}
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h2 className="text-xl font-bold text-white">{currentFailure.error_type}</h2>
                      <Badge variant={currentFailure.ci_provider || 'github_actions'}>
                        {currentFailure.ci_provider === 'jenkins' ? 'Jenkins CI' : 'GitHub Actions CI'}
                      </Badge>
                      <Badge variant={currentFailure.severity}>{currentFailure.severity}</Badge>
                    </div>
                    <p className="text-xs text-slate-400 font-mono">Failure ID: {currentFailure.id}</p>
                  </div>

                  <button
                    onClick={handleLaunchInvestigation}
                    disabled={isInvestigating}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-medium text-xs transition shadow-lg shadow-brand-600/25 disabled:opacity-50"
                  >
                    <Sparkles className={`w-4 h-4 ${isInvestigating ? 'animate-spin' : ''}`} />
                    <span>{isInvestigating ? 'Orchestrating Agents...' : 'Run Multi-Agent RCA'}</span>
                  </button>
                </div>

                {/* Score Separation (Rule §6) */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800 text-xs">
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block text-[11px]">Classification:</span>
                    <span className="font-bold text-slate-100">{currentFailure.classification}</span>
                    <span className="text-[10px] text-slate-500 block">Conf: {Math.round(currentFailure.classification_confidence * 100)}%</span>
                  </div>

                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block text-[11px]">Regression Prob:</span>
                    <span className="font-bold text-rose-300 font-mono text-sm">{Math.round(currentFailure.regression_prob * 100)}%</span>
                    <span className="text-[10px] text-slate-500 block">Code change impact</span>
                  </div>

                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block text-[11px]">Flakiness Score:</span>
                    <span className="font-bold text-purple-300 font-mono text-sm">{Math.round(currentFailure.flakiness_score * 100)}%</span>
                    <span className="text-[10px] text-slate-500 block">Intermittent probability</span>
                  </div>

                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block text-[11px]">Severity (Impact):</span>
                    <span className="font-bold text-slate-100">{currentFailure.severity}</span>
                    <span className="text-[10px] text-slate-500 block">Independent impact</span>
                  </div>
                </div>
              </div>

              {/* Fingerprint & Deduplication Card */}
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <FingerprintIcon className="w-4 h-4 text-brand-400" />
                  <h3 className="text-sm font-semibold text-white">Canonical Failure Fingerprint</h3>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 font-mono text-xs flex items-center justify-between">
                  <span className="text-slate-400 truncate">
                    Hash: <span className="text-brand-300">{currentFailure.fingerprint_id || 'fp-8f92a30b...'}</span>
                  </span>
                  <span className="text-emerald-400 shrink-0 ml-2">De-duplicated across runs</span>
                </div>
              </div>

              {/* Log Viewer with Syntax Highlighting / Sanitization */}
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-brand-400" />
                    <h3 className="text-sm font-semibold text-white">Stack Trace & Failure Console Log</h3>
                  </div>
                  <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                    <button
                      onClick={() => setActiveView('normalized')}
                      className={`px-2.5 py-1 rounded text-xs transition ${
                        activeView === 'normalized' ? 'bg-brand-600 text-white font-medium' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Normalized & Sanitized
                    </button>
                    <button
                      onClick={() => setActiveView('raw')}
                      className={`px-2.5 py-1 rounded text-xs transition ${
                        activeView === 'raw' ? 'bg-brand-600 text-white font-medium' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Raw Trace
                    </button>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs leading-relaxed text-slate-200 overflow-x-auto max-h-96">
                  <div className="text-slate-400 pb-2 mb-2 border-b border-slate-800 text-[11px] flex items-center justify-between">
                    <span>
                      {activeView === 'normalized' 
                        ? 'Tokenized: ANSI stripped, timestamps normalized, secrets masked [REDACTED_SECRET]' 
                        : 'Raw CI runner output'}
                    </span>
                  </div>
                  <pre className="whitespace-pre-wrap">
                    {activeView === 'normalized' 
                      ? (currentFailure.normalized_stack_trace || currentFailure.normalized_message)
                      : (currentFailure.raw_stack_trace || currentFailure.raw_message)}
                  </pre>
                </div>
              </div>
            </>
          ) : (
            <div className="rounded-xl bg-slate-900 border border-slate-800 p-12 text-center text-slate-400">
              Select a failure from the left list to view detailed triage and analysis.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
