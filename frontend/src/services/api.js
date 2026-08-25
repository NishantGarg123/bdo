import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

function getCookieValue(name) {
  const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return match ? decodeURIComponent(match[2]) : null;
}

let csrfTokenFetched = false;

export async function fetchCSRFToken() {
  // Calls the endpoint decorated with @ensure_csrf_cookie so Django sets
  // the csrftoken cookie. The actual token value is then read from the
  // cookie per-request rather than stored in a variable that can go stale.
  if (!csrfTokenFetched) {
    await api.get('/csrf/');
    csrfTokenFetched = true;
  }
}

api.interceptors.request.use((config) => {
  if (['post', 'put', 'patch', 'delete'].includes(config.method)) {
    const token = getCookieValue('csrftoken');
    if (token) {
      config.headers['X-CSRFToken'] = token;
    }
  }
  return config;
});

export const authAPI = {
  login: (username, password) => api.post('/login/', { username, password }),
  logout: () => api.post('/logout/'),
  getCurrentUser: () => api.get('/me/'),
};

export const dashboardAPI = {
  getStats: () => api.get('/dashboard/'),
};

export const leadsAPI = {
  getAll: (params) => api.get('/leads/', { params }),
  getApplied: (params) => api.get('/leads/applied/', { params }),
  getRejected: (params) => api.get('/leads/rejected/', { params }),
  create: (data) => api.post('/leads/', data),
  getById: (id) => api.get(`/leads/${id}/`),
  getAnalysis: (id) => api.get(`/leads/${id}/analysis/`),
  updateAnalysis: (id, data) => api.patch(`/leads/${id}/analysis/`, data),
  update: (id, data) => api.patch(`/leads/${id}/`, data),
  apply: (id) => api.post(`/leads/${id}/apply/`),
  reject: (id, rejection_reason) => api.post(`/leads/${id}/reject/`, { rejection_reason }),
  revertToAnalyzed: (id) => api.post(`/leads/${id}/revert-to-analyzed/`),
  delete: (id) => api.delete(`/leads/${id}/`),
  bulkRefresh: (ids) => api.post('/leads/bulk-refresh/', { ids }),
};

export const activityAPI = {
  getAll: () => api.get('/activity/'),
};

export const integrationsAPI = {
  getAll: () => api.get('/integrations/'),
};

export const projectsAPI = {
  getAll: (params) => api.get('/projects/', { params }),
  create: (data) => api.post('/projects/', data),
  getById: (id) => api.get(`/projects/${id}/`),
  update: (id, data) => api.patch(`/projects/${id}/`, data),
  getIssues: (projectId, params) => api.get(`/projects/${projectId}/issues/`, { params }),
  createIssue: (projectId, data) => api.post(`/projects/${projectId}/issues/`, data),
  getIssue: (id) => api.get(`/issues/${id}/`),
  updateIssue: (id, data) => api.patch(`/issues/${id}/`, data),
  getKnowledgeBase: (params) => api.get('/knowledge-base/', { params }),
  getFAQs: (projectId) => api.get(`/projects/${projectId}/faqs/`),
  createFAQ: (projectId, data) => api.post(`/projects/${projectId}/faqs/`, data),
  updateFAQ: (id, data) => api.patch(`/faqs/${id}/`, data),
  deleteFAQ: (id) => api.delete(`/faqs/${id}/`),
};

export const agentAPI = {
  askQuestion: (data) => api.post('/projects/agent/chat/', data),
};

export default api;
