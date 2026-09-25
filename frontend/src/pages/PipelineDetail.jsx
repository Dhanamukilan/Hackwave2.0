import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  GitCommit,
  Clock,
  CheckCircle,
  XCircle,
  PlusCircle,
  Upload,
  RefreshCw,
  Search,
  ExternalLink
} from 'lucide-react';
import { api } from '../services/api';
import { Badge } from '../components/Badge';

export function PipelineDetail({ onSelectFailure }) {
  const [builds, setBuilds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterBranch, setFilterBranch] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [showIngestModal, setShowIngestModal] = useState(false);
  const [ingestPayload, setIngestPayload] = useState({
    repoName: 'demo-pipeline-repo',
    pipelineName: 'CI / Main Build',
    commitSha: 'commit-e4f8a12c',
    branch: 'main',
    junitXml: `<testsuites>
  <testsuite name="order_processing" tests="3">
    <testcase classname="test_order" name="test_create_order" time="0.12"/>
    <testcase classname="test_order" name="test_discount_calculation" time="0.08"/>
    <testcase classname="test_order" name="test_payment_gateway_charge" time="0.25">
      <failure message="AssertionError: assert 500 == 200 in payment charge" type="AssertionError">
File "services/payment.py", line 88, in process_payment
assert response.status_code == 200, f"Expected 200 but received {response.status_code}"
AssertionError: assert 500 == 200
      </failure>
    </testcase>
  </testsuite>
</testsuites>`,
  });

  const loadBuilds = async () => {
    setLoading(true);
    try {
      const data = await api.getBuilds(50);
      setBuilds(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBuilds();
  }, []);

  const handleIngest = async (e) => {
    e.preventDefault();
    try {
      await api.ingestExecution({
        repository_name: ingestPayload.repoName,
        pipeline_name: ingestPayload.pipelineName,
        commit_sha: ingestPayload.commitSha,
        branch: ingestPayload.branch,
        junit_xml: ingestPayload.junitXml,
      });
      setShowIngestModal(false);
      loadBuilds();
      alert('Test execution report ingested successfully!');
    } catch (err) {
      alert(err.message || 'Ingestion failed');
    }
  };

  const filteredBuilds = builds.filter((b) => {
    if (filterBranch !== 'ALL' && b.branch !== filterBranch) return false;
    if (filterStatus !== 'ALL' && b.status !== filterStatus) return false;
    return true;
  });

  const branches = Array.from(new Set(builds.map((b) => b.branch)));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Pipelines & Builds</h1>
          <p className="text-sm text-slate-400">CI/CD execution history, build telemetry, and test results</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowIngestModal(true)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition shadow"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Ingest Test Report</span>
          </button>
          <button
            onClick={loadBuilds}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs">
        <span className="text-slate-400 font-medium">Filter by:</span>
        <select
          value={filterBranch}
          onChange={(e) => setFilterBranch(e.target.value)}
          className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-brand-500"
        >
          <option value="ALL">All Branches</option>
          {branches.map((br) => (
            <option key={br} value={br}>{br}</option>
          ))}
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-brand-500"
        >
          <option value="ALL">All Statuses</option>
          <option value="SUCCESS">Success Only</option>
          <option value="FAILURE">Failure Only</option>
        </select>
      </div>

      {/* Builds Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-2.5">Build #</th>
                <th className="py-2.5">Branch</th>
                <th className="py-2.5">Commit</th>
                <th className="py-2.5">Status</th>
                <th className="py-2.5">Duration</th>
                <th className="py-2.5">Started At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredBuilds.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400 font-sans">
                    No builds found matching the selected filters.
                  </td>
                </tr>
              ) : (
                filteredBuilds.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-850/60 transition">
                    <td className="py-3 font-semibold text-slate-200">
                      #{b.build_number}
                    </td>
                    <td className="py-3 font-sans">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <GitBranch className="w-3.5 h-3.5 text-slate-400" />
                        <span>{b.branch}</span>
                      </div>
                    </td>
                    <td className="py-3 text-slate-400">
                      <div className="flex items-center gap-1">
                        <GitCommit className="w-3.5 h-3.5" />
                        <span>{b.commit_sha ? b.commit_sha.slice(0, 8) : 'sha'}</span>
                      </div>
                    </td>
                    <td className="py-3">
                      <Badge variant={b.status}>{b.status}</Badge>
                    </td>
                    <td className="py-3 text-slate-300 font-sans">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        <span>{b.duration_seconds.toFixed(2)}s</span>
                      </div>
                    </td>
                    <td className="py-3 text-slate-400 font-sans">
                      {new Date(b.started_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ingest Modal */}
      {showIngestModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-lg font-bold text-white">Ingest Test Execution Report</h2>
              <button
                onClick={() => setShowIngestModal(false)}
                className="text-slate-400 hover:text-white"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleIngest} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Repository Name</label>
                  <input
                    type="text"
                    value={ingestPayload.repoName}
                    onChange={(e) => setIngestPayload({ ...ingestPayload, repoName: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Pipeline Name</label>
                  <input
                    type="text"
                    value={ingestPayload.pipelineName}
                    onChange={(e) => setIngestPayload({ ...ingestPayload, pipelineName: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Commit SHA</label>
                  <input
                    type="text"
                    value={ingestPayload.commitSha}
                    onChange={(e) => setIngestPayload({ ...ingestPayload, commitSha: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Branch</label>
                  <input
                    type="text"
                    value={ingestPayload.branch}
                    onChange={(e) => setIngestPayload({ ...ingestPayload, branch: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">JUnit XML Content</label>
                <textarea
                  rows={8}
                  value={ingestPayload.junitXml}
                  onChange={(e) => setIngestPayload({ ...ingestPayload, junitXml: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono text-[11px]"
                  required
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowIngestModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-medium"
                >
                  Parse & Ingest
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
