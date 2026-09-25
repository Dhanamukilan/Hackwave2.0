import React, { useState, useEffect } from 'react';
import {
  FileSearch,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ShieldCheck,
  AlertCircle,
  Play,
  ThumbsUp,
  ThumbsDown,
  Sparkles,
  Terminal,
  Code,
  Tag
} from 'lucide-react';
import { api } from '../services/api';
import { Badge } from '../components/Badge';

export function RCAView({ selectedInvestigationId }) {
  const [investigations, setInvestigations] = useState([]);
  const [currentInv, setCurrentInv] = useState(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackForm, setFeedbackForm] = useState({
    isCorrect: true,
    actualClass: 'REGRESSION',
    comments: '',
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.getInvestigations();
      setInvestigations(data);
      if (selectedInvestigationId) {
        const found = data.find((i) => i.id === selectedInvestigationId);
        setCurrentInv(found || data[0] || null);
      } else if (data.length > 0) {
        setCurrentInv(data[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedInvestigationId]);

  const handleApproveRemediation = async (remediationId) => {
    if (!currentInv) return;
    setApproving(true);
    try {
      const res = await api.approveRemediation(currentInv.id, remediationId);
      alert(`Remediation action approved! Result: ${res.execution_result?.action || 'Executed'}`);
      loadData();
    } catch (e) {
      alert(e.message || 'Approval failed. Verify your role is ADMIN or INVESTIGATOR.');
    } finally {
      setApproving(false);
    }
  };

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!currentInv) return;
    try {
      await api.submitFeedback(
        currentInv.id,
        feedbackForm.isCorrect,
        feedbackForm.actualClass,
        feedbackForm.comments
      );
      setFeedbackSubmitted(true);
      setTimeout(() => setFeedbackSubmitted(false), 4000);
    } catch (e) {
      alert(e.message || 'Failed to submit feedback');
    }
  };

  const hypotheses = currentInv?.hypotheses_evaluated || [];
  const remediations = currentInv?.remediations || [];
  const evidenceItems = currentInv?.evidence_bundle?.evidence_items || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Root Cause Analysis & Remediation</h1>
          <p className="text-sm text-slate-400">Hypotheses H1–H7 evidence matrix with human approval gate</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Investigation selector (4 cols) */}
        <div className="lg:col-span-4 rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="font-semibold text-xs text-slate-300 uppercase tracking-wider">
              Investigations ({investigations.length})
            </span>
          </div>

          <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
            {investigations.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">
                No RCA investigations run yet. Launch an investigation from Failure Triage.
              </p>
            ) : (
              investigations.map((inv) => {
                const isSelected = currentInv && currentInv.id === inv.id;
                return (
                  <div
                    key={inv.id}
                    onClick={() => setCurrentInv(inv)}
                    className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-brand-950/40 border-brand-500 shadow-md shadow-brand-500/10'
                        : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-xs font-semibold text-slate-200">Investigation</span>
                      <Badge variant={inv.status}>{inv.status}</Badge>
                    </div>
                    <div className="text-[11px] text-slate-400 line-clamp-2 mb-2 font-mono">
                      {inv.rca_summary || 'Analysis in progress...'}
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1.5 border-t border-slate-800">
                      <span>Confidence: {inv.confidence}</span>
                      <span className="font-mono text-slate-400">
                        {new Date(inv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RCA View Details (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {currentInv ? (
            <>
              {/* RCA Conclusion Banner */}
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Sparkles className="w-5 h-5 text-brand-400" />
                      <h2 className="text-lg font-bold text-white">Root Cause Conclusion</h2>
                      <span className={`text-xs px-2 py-0.5 rounded font-semibold font-mono border ${
                        currentInv.confidence === 'HIGH' ? 'bg-emerald-950 text-emerald-300 border-emerald-800' :
                        currentInv.confidence === 'MEDIUM' ? 'bg-amber-950 text-amber-300 border-amber-800' :
                        'bg-slate-800 text-slate-300 border-slate-700'
                      }`}>
                        {currentInv.confidence} CONFIDENCE
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 font-mono">
                      Evidence-backed reasoning citing retrieved artifacts only (Section §4 Contract)
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 leading-relaxed font-sans">
                  {currentInv.rca_summary}
                </div>
              </div>

              {/* Hypotheses H1..H7 Evaluation Matrix */}
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Hypotheses H1–H7 Evaluation Matrix</h3>
                  <span className="text-xs text-slate-400 font-mono">Rule-Checked & Verifiable</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                      <tr>
                        <th className="py-2.5">Hypothesis</th>
                        <th className="py-2.5">Outcome</th>
                        <th className="py-2.5">Supporting Evidence IDs</th>
                        <th className="py-2.5">Contradicting</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {hypotheses.map((h) => {
                        const isConfirmed = h.status === 'CONFIRMED';
                        return (
                          <tr key={h.hypothesis_id} className={`transition ${isConfirmed ? 'bg-emerald-950/20' : 'hover:bg-slate-850/50'}`}>
                            <td className="py-3 font-sans pr-2">
                              <div className="font-semibold text-slate-200">
                                {h.hypothesis_id}: {h.title}
                              </div>
                              <div className="text-[11px] text-slate-400 font-mono">Score: {h.score}</div>
                            </td>
                            <td className="py-3">
                              <span className={`inline-flex items-center gap-1 font-sans text-xs px-2 py-0.5 rounded font-medium ${
                                h.status === 'CONFIRMED' ? 'text-emerald-400 bg-emerald-950/60 border border-emerald-800' :
                                h.status === 'REFUTED' ? 'text-slate-400 bg-slate-950 border border-slate-800' :
                                'text-amber-400 bg-amber-950/60 border border-amber-800'
                              }`}>
                                {h.status === 'CONFIRMED' && <CheckCircle2 className="w-3.5 h-3.5" />}
                                {h.status === 'REFUTED' && <XCircle className="w-3.5 h-3.5" />}
                                {h.status === 'INSUFFICIENT_EVIDENCE' && <HelpCircle className="w-3.5 h-3.5" />}
                                <span>{h.status}</span>
                              </span>
                            </td>
                            <td className="py-3">
                              <div className="flex flex-wrap gap-1">
                                {h.supporting_evidence_ids && h.supporting_evidence_ids.length > 0 ? (
                                  h.supporting_evidence_ids.map((eid) => (
                                    <span key={eid} className="px-1.5 py-0.5 bg-brand-950 border border-brand-800 text-brand-300 rounded text-[10px] font-mono">
                                      {eid}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-slate-400 text-[11px] font-sans">None</span>
                                )}
                              </div>
                            </td>
                            <td className="py-3">
                              <div className="flex flex-wrap gap-1">
                                {h.contradicting_evidence_ids && h.contradicting_evidence_ids.length > 0 ? (
                                  h.contradicting_evidence_ids.map((eid) => (
                                    <span key={eid} className="px-1.5 py-0.5 bg-rose-950 border border-rose-800 text-rose-300 rounded text-[10px] font-mono">
                                      {eid}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-slate-400 text-[11px] font-sans">None</span>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Evidence Bundle Repository */}
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <Tag className="w-4 h-4 text-brand-400" />
                  <h3 className="text-sm font-semibold text-white">Retrieved Evidence Items</h3>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {evidenceItems.map((item) => (
                    <div key={item.evidence_id} className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-brand-400 font-semibold">{item.evidence_id}</span>
                        <span className="text-[10px] text-slate-400">{item.evidence_type}</span>
                      </div>
                      <p className="text-slate-300 text-[11px] font-medium">{item.summary}</p>
                      <div className="text-[10px] text-slate-400 font-mono truncate">Source: {item.source}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Human Approval Gate & Remediation */}
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                    <h3 className="text-sm font-semibold text-white">Recommended Remediation (Human Approval Gate)</h3>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">Section §7 Security Enforced</span>
                </div>

                {remediations.map((rem) => (
                  <div key={rem.id} className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-sm text-slate-200">{rem.action_type}</span>
                          <Badge variant={rem.status}>{rem.status}</Badge>
                        </div>
                        <p className="text-xs text-slate-300">{rem.proposed_action}</p>
                      </div>

                      {rem.status === 'PENDING_APPROVAL' ? (
                        <button
                          onClick={() => handleApproveRemediation(rem.id)}
                          disabled={approving}
                          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shrink-0 shadow-lg shadow-emerald-600/20 disabled:opacity-50"
                        >
                          <Play className="w-3.5 h-3.5" />
                          <span>{approving ? 'Executing...' : 'Approve & Execute'}</span>
                        </button>
                      ) : (
                        <span className="text-xs font-mono text-emerald-400 flex items-center gap-1 font-semibold">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Approved & Executed</span>
                        </span>
                      )}
                    </div>

                    {rem.diff_or_script && (
                      <div className="p-3 bg-slate-900 rounded-lg border border-slate-800/80 font-mono text-[11px] text-slate-300 overflow-x-auto">
                        <pre>{rem.diff_or_script}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Continuous Feedback Form */}
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-3">
                <h3 className="text-sm font-semibold text-white">Continuous Feedback Loop</h3>
                <p className="text-xs text-slate-400">Validate this triage decision to calibrate future model runs.</p>

                {feedbackSubmitted ? (
                  <div className="p-3 bg-emerald-950/40 border border-emerald-800 rounded-lg text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Feedback received! Added to the historical learning dataset.</span>
                  </div>
                ) : (
                  <form onSubmit={handleFeedbackSubmit} className="space-y-3 text-xs">
                    <div className="flex items-center gap-4">
                      <span className="text-slate-300">Was the RCA accurate?</span>
                      <button
                        type="button"
                        onClick={() => setFeedbackForm({ ...feedbackForm, isCorrect: true })}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg border transition ${
                          feedbackForm.isCorrect
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-600 font-semibold'
                            : 'bg-slate-950 text-slate-400 border-slate-800'
                        }`}
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                        <span>Yes</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setFeedbackForm({ ...feedbackForm, isCorrect: false })}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg border transition ${
                          !feedbackForm.isCorrect
                            ? 'bg-rose-950 text-rose-300 border-rose-600 font-semibold'
                            : 'bg-slate-950 text-slate-400 border-slate-800'
                        }`}
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                        <span>No</span>
                      </button>
                    </div>

                    <div>
                      <input
                        type="text"
                        placeholder="Optional comments or developer observations..."
                        value={feedbackForm.comments}
                        onChange={(e) => setFeedbackForm({ ...feedbackForm, comments: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 placeholder:text-slate-600"
                      />
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="submit"
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium"
                      >
                        Submit Calibration Feedback
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </>
          ) : (
            <div className="rounded-xl bg-slate-900 border border-slate-800 p-12 text-center text-slate-400">
              Select an investigation from the left to view the hypothesis matrix and remediation plan.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
