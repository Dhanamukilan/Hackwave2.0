import React, { useState, useEffect } from 'react';
import {
  Shield,
  Users,
  Key,
  Webhook,
  Cpu,
  History,
  CheckCircle,
  AlertCircle,
  Copy,
  PlusCircle,
  Lock
} from 'lucide-react';
import { api } from '../services/api';
import { Badge } from '../components/Badge';

export function SettingsRBAC({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddUser, setShowAddUser] = useState(false);
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    password: '',
    role: 'DEVELOPER',
  });
  const [copied, setCopied] = useState(false);

  const webhookUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/v1/webhooks/github`;

  const loadData = async () => {
    setLoading(true);
    try {
      const [uList, logs] = await Promise.all([
        api.getUsers().catch(() => []),
        api.getAuditLogs(30).catch(() => []),
      ]);
      setUsers(uList);
      setAuditLogs(logs);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await api.register(newUser.username, newUser.email, newUser.password, newUser.role);
      setShowAddUser(false);
      setNewUser({ username: '', email: '', password: '', role: 'DEVELOPER' });
      loadData();
      alert('User registered successfully!');
    } catch (e) {
      alert(e.message || 'Failed to create user');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">System Settings & RBAC</h1>
        <p className="text-sm text-slate-400">User roles, webhook registration, local model configuration, and audit trails</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* GitHub Webhook Setup */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Webhook className="w-5 h-5 text-brand-400" />
            <h2 className="font-semibold text-white text-sm">GitHub Webhook Integration</h2>
          </div>
          <p className="text-xs text-slate-400">
            Register this webhook in your real GitHub repository settings under <strong>Webhooks &rarr; Add webhook</strong>.
          </p>

          <div className="space-y-3 text-xs">
            <div>
              <span className="text-slate-400 block mb-1">Payload URL:</span>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={webhookUrl}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-[11px] text-slate-200"
                />
                <button
                  onClick={() => copyToClipboard(webhookUrl)}
                  className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition shrink-0"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </div>
              {copied && <span className="text-[10px] text-emerald-400 mt-1 block">Copied to clipboard!</span>}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-slate-400 block mb-1">Content type:</span>
                <span className="font-mono text-slate-200 bg-slate-950 px-2 py-1 rounded block border border-slate-800">
                  application/json
                </span>
              </div>
              <div>
                <span className="text-slate-400 block mb-1">Secret signature:</span>
                <span className="font-mono text-slate-200 bg-slate-950 px-2 py-1 rounded block border border-slate-800">
                  HMAC-SHA256 (env)
                </span>
              </div>
            </div>

            <div>
              <span className="text-slate-400 block mb-1">Subscribed Events:</span>
              <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                <span className="px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-slate-300">push</span>
                <span className="px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-slate-300">pull_request</span>
                <span className="px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-slate-300">workflow_run</span>
                <span className="px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-slate-300">check_run</span>
              </div>
            </div>
          </div>
        </div>

        {/* Local LLM Settings */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" />
            <h2 className="font-semibold text-white text-sm">Local Model Architecture</h2>
          </div>
          <p className="text-xs text-slate-400">
            Open-source reasoning layer running locally via Ollama / OpenAI-compatible endpoint.
          </p>

          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-slate-400 block mb-1">Provider:</span>
                <span className="font-mono text-slate-200 bg-slate-950 px-2.5 py-1.5 rounded block border border-slate-800">
                  Ollama / Local v1
                </span>
              </div>
              <div>
                <span className="text-slate-400 block mb-1">Model Name:</span>
                <span className="font-mono text-brand-300 bg-slate-950 px-2.5 py-1.5 rounded block border border-slate-800">
                  llama3.1:8b
                </span>
              </div>
            </div>

            <div>
              <span className="text-slate-400 block mb-1">Endpoint URL:</span>
              <span className="font-mono text-slate-300 bg-slate-950 px-2.5 py-1.5 rounded block border border-slate-800">
                http://localhost:11434/v1
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-400 leading-relaxed">
              <span className="text-emerald-400 font-semibold block mb-0.5">Strict Evidence Boundary (§4 Contract):</span>
              The prompt template forbids inventing unverified claims. The model only reasons over retrieved database artifacts and cited evidence IDs.
            </div>
          </div>
        </div>
      </div>

      {/* User Management & RBAC */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-sky-400" />
            <h2 className="font-semibold text-white text-sm">Role-Based Access Control (RBAC)</h2>
          </div>
          <button
            onClick={() => setShowAddUser(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Add User</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-2.5">Username</th>
                <th className="py-2.5">Email</th>
                <th className="py-2.5">Assigned Role</th>
                <th className="py-2.5">Status</th>
                <th className="py-2.5">Permissions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-850/50">
                  <td className="py-3 font-semibold text-slate-200">{u.username}</td>
                  <td className="py-3 text-slate-400 font-mono text-[11px]">{u.email}</td>
                  <td className="py-3">
                    <Badge variant={u.role}>{u.role}</Badge>
                  </td>
                  <td className="py-3">
                    <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
                      <CheckCircle className="w-3.5 h-3.5" /> Active
                    </span>
                  </td>
                  <td className="py-3 text-[11px] text-slate-400">
                    {u.role === 'ADMIN' && 'Full platform control, user management, remediation approval'}
                    {u.role === 'INVESTIGATOR' && 'Trigger RCA, approve remediations, calibrate feedback'}
                    {u.role === 'DEVELOPER' && 'Inspect failures, run investigations, submit feedback'}
                    {u.role === 'VIEWER' && 'Read-only pipeline and dashboard telemetry'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live Audit Log */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-amber-400" />
          <h2 className="font-semibold text-white text-sm">Security & Mutation Audit Trail</h2>
        </div>
        <p className="text-xs text-slate-400">Immutable record of API mutations, triage executions, and state changes</p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-2.5">Timestamp</th>
                <th className="py-2.5">Action</th>
                <th className="py-2.5">Resource</th>
                <th className="py-2.5">Client IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-[11px]">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-4 text-center text-slate-400 font-sans">
                    No mutation audit records recorded yet.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-850/50">
                    <td className="py-2.5 text-slate-400">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </td>
                    <td className="py-2.5 text-slate-200 font-semibold">{log.action}</td>
                    <td className="py-2.5 text-brand-300">{log.resource_id}</td>
                    <td className="py-2.5 text-slate-400">{log.ip_address || '127.0.0.1'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddUser && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-lg font-bold text-white">Create New User</h2>
              <button onClick={() => setShowAddUser(false)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Username</label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                  required
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Email</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                  required
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Password</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                  required
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Role</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                >
                  <option value="DEVELOPER">DEVELOPER</option>
                  <option value="INVESTIGATOR">INVESTIGATOR</option>
                  <option value="ADMIN">ADMIN</option>
                  <option value="VIEWER">VIEWER</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddUser(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-medium"
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
