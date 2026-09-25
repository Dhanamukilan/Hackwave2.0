const API_BASE = '/api/v1';

function getAuthHeaders() {
  const token = localStorage.getItem('ag004_token');
  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  // Auth
  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    localStorage.setItem('ag004_token', data.access_token);
    localStorage.setItem('ag004_user', JSON.stringify(data.user));
    return data;
  },

  async register(username, email, password, role = 'DEVELOPER') {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password, role }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Registration failed');
    }
    return res.json();
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch user profile');
    return res.json();
  },

  async getUsers() {
    const res = await fetch(`${API_BASE}/auth/users`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch users list');
    return res.json();
  },

  async changePassword(oldPassword, newPassword) {
    const res = await fetch(`${API_BASE}/auth/change-password`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Password change failed');
    }
    const user = await res.json();
    localStorage.setItem('ag004_user', JSON.stringify(user));
    return user;
  },

  logout() {
    localStorage.removeItem('ag004_token');
    localStorage.removeItem('ag004_user');
  },

  getCurrentUser() {
    const u = localStorage.getItem('ag004_user');
    return u ? JSON.parse(u) : null;
  },

  // Pipelines & Builds
  async getPipelines() {
    const res = await fetch(`${API_BASE}/pipelines`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch pipelines');
    return res.json();
  },

  async getBuilds(limit = 25) {
    const res = await fetch(`${API_BASE}/builds?limit=${limit}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch builds');
    return res.json();
  },

  async getBuildDetail(buildId) {
    const res = await fetch(`${API_BASE}/builds/${buildId}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch build detail');
    return res.json();
  },

  async getTests(minFlakiness = 0.0) {
    const res = await fetch(`${API_BASE}/tests?min_flakiness=${minFlakiness}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch tests');
    return res.json();
  },

  // Failures & Fingerprints
  async getFailures(classification = '', severity = '', limit = 50) {
    let url = `${API_BASE}/failures?limit=${limit}`;
    if (classification) url += `&classification=${classification}`;
    if (severity) url += `&severity=${severity}`;
    const res = await fetch(url, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch failures');
    return res.json();
  },

  async getFailureDetail(failureId) {
    const res = await fetch(`${API_BASE}/failures/${failureId}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch failure details');
    return res.json();
  },

  async getFingerprints(limit = 20) {
    const res = await fetch(`${API_BASE}/failures/fingerprints?limit=${limit}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch fingerprints');
    return res.json();
  },

  async triggerInvestigation(failureId) {
    const res = await fetch(`${API_BASE}/failures/${failureId}/investigate`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to trigger investigation');
    }
    return res.json();
  },

  async ingestExecution(payload) {
    const res = await fetch(`${API_BASE}/failures/ingest`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to ingest execution');
    }
    return res.json();
  },

  // Investigations & Remediation
  async getInvestigations() {
    const res = await fetch(`${API_BASE}/investigations`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch investigations');
    return res.json();
  },

  async getInvestigationDetail(investigationId) {
    const res = await fetch(`${API_BASE}/investigations/${investigationId}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch investigation detail');
    return res.json();
  },

  async approveRemediation(investigationId, remediationId) {
    const res = await fetch(`${API_BASE}/investigations/${investigationId}/remediations/${remediationId}/approve`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to approve remediation');
    }
    return res.json();
  },

  async submitFeedback(investigationId, isRcaCorrect, actualClassification, comments) {
    const res = await fetch(`${API_BASE}/investigations/feedback`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        investigation_id: investigationId,
        is_rca_correct: isRcaCorrect,
        actual_classification: actualClassification,
        comments: comments,
      }),
    });
    if (!res.ok) throw new Error('Failed to submit feedback');
    return res.json();
  },

  // ML Metrics (Cold start evaluation)
  async getMLMetrics() {
    const res = await fetch(`${API_BASE}/ml/metrics`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch ML evaluation metrics');
    return res.json();
  },

  // Audit Logs
  async getAuditLogs(limit = 100) {
    const res = await fetch(`${API_BASE}/audit/logs?limit=${limit}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('Failed to fetch audit logs');
    return res.json();
  },
};
