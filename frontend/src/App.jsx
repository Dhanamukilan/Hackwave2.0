import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { PipelineDetail } from './pages/PipelineDetail';
import { FailureInvestigation } from './pages/FailureInvestigation';
import { RCAView } from './pages/RCAView';
import { SettingsRBAC } from './pages/SettingsRBAC';
import { api } from './services/api';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [user, setUser] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [changePasswordForm, setChangePasswordForm] = useState({ oldPassword: '', newPassword: '' });
  const [passwordError, setPasswordError] = useState('');
  const [selectedFailureId, setSelectedFailureId] = useState(null);
  const [selectedInvestigationId, setSelectedInvestigationId] = useState(null);

  useEffect(() => {
    // Attempt to restore existing logged in user session
    const stored = api.getCurrentUser();
    if (stored) {
      setUser(stored);
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const data = await api.login(loginForm.username, loginForm.password);
      setUser(data.user);
      setShowLoginModal(false);
      setLoginForm({ username: '', password: '' });
    } catch (e) {
      alert(e.message || 'Login failed');
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');
    if (changePasswordForm.newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters.');
      return;
    }
    if (changePasswordForm.oldPassword === changePasswordForm.newPassword) {
      setPasswordError('New password must be different from current temporary password.');
      return;
    }
    try {
      const updatedUser = await api.changePassword(
        changePasswordForm.oldPassword,
        changePasswordForm.newPassword
      );
      setUser(updatedUser);
      setChangePasswordForm({ oldPassword: '', newPassword: '' });
      alert('Password updated successfully! Full platform access granted.');
    } catch (e) {
      setPasswordError(e.message || 'Failed to update password');
    }
  };

  const handleLogout = () => {
    api.logout();
    setUser(null);
  };

  const handleSelectFailureFromDashboard = (failureId, investigationId) => {
    setSelectedFailureId(failureId);
    setSelectedInvestigationId(investigationId);
    setActiveTab('rca');
  };

  const handleNavigateToRCA = (investigationId) => {
    setSelectedInvestigationId(investigationId);
    setActiveTab('rca');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar
        user={user}
        onLogout={handleLogout}
        onOpenLogin={() => setShowLoginModal(true)}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="flex-1 overflow-y-auto p-8 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
          <div className="max-w-7xl mx-auto">
            {activeTab === 'dashboard' && (
              <Dashboard
                onSelectFailure={handleSelectFailureFromDashboard}
                onNavigateTab={(tab) => setActiveTab(tab)}
              />
            )}
            {activeTab === 'pipelines' && (
              <PipelineDetail
                onSelectFailure={(fid) => {
                  setSelectedFailureId(fid);
                  setActiveTab('failures');
                }}
              />
            )}
            {activeTab === 'failures' && (
              <FailureInvestigation
                selectedFailureId={selectedFailureId}
                onNavigateToRCA={handleNavigateToRCA}
              />
            )}
            {activeTab === 'rca' && (
              <RCAView
                selectedInvestigationId={selectedInvestigationId}
              />
            )}
            {activeTab === 'settings' && (
              <SettingsRBAC currentUser={user} />
            )}
          </div>
        </main>
      </div>

      {/* Login Modal */}
      {showLoginModal && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-sm p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h2 className="text-base font-bold text-white">Sign In to AG004</h2>
              <button onClick={() => setShowLoginModal(false)} className="text-slate-400 hover:text-white">&times;</button>
            </div>

            <form onSubmit={handleLogin} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Username</label>
                <input
                  type="text"
                  value={loginForm.username}
                  onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200"
                  required
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Password</label>
                <input
                  type="password"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200"
                  required
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  className="w-full py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-medium transition shadow-md"
                >
                  Authenticate
                </button>
              </div>

              <div className="mt-3 p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <div className="font-semibold text-slate-300">Admin Credentials:</div>
                <div className="flex justify-between">
                  <span>Username:</span>
                  <span className="font-mono text-emerald-400 font-medium">admin</span>
                </div>
                <div className="flex justify-between">
                  <span>Password:</span>
                  <span className="font-mono text-emerald-400 font-medium">NewPermanentAdminPass456!</span>
                </div>
                <button
                  type="button"
                  onClick={() => setLoginForm({ username: 'admin', password: 'NewPermanentAdminPass456!' })}
                  className="w-full mt-2 py-1 text-center text-xs font-medium text-brand-400 hover:text-brand-300 bg-brand-950/50 hover:bg-brand-900/50 border border-brand-800/60 rounded transition"
                >
                  Auto-fill Credentials
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Mandatory Forced Password Change Modal */}
      {user && user.must_change_password && (
        <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4 backdrop-blur-md">
          <div className="bg-slate-900 border border-amber-500/50 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800 text-amber-400">
              <span className="text-xl">⚠️</span>
              <h2 className="text-base font-bold text-white">Password Change Required</h2>
            </div>

            <p className="text-xs text-slate-400">
              This account was initialized with a one-time bootstrap credential. You must establish a secure permanent password (minimum 8 characters) before continuing.
            </p>

            {passwordError && (
              <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {passwordError}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Temporary / Bootstrap Password</label>
                <input
                  type="password"
                  value={changePasswordForm.oldPassword}
                  onChange={(e) => setChangePasswordForm({ ...changePasswordForm, oldPassword: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200"
                  required
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">New Permanent Password</label>
                <input
                  type="password"
                  value={changePasswordForm.newPassword}
                  onChange={(e) => setChangePasswordForm({ ...changePasswordForm, newPassword: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200"
                  placeholder="Minimum 8 characters"
                  required
                />
              </div>

              <div className="pt-2 flex items-center gap-3">
                <button
                  type="submit"
                  className="flex-1 py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium transition shadow-md"
                >
                  Set New Password
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition"
                >
                  Sign Out
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
export default App;
