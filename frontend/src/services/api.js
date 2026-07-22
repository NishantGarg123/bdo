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
  create: (data) => api.post('/leads/', data),
  getById: (id) => api.get(`/leads/${id}/`),
  getAnalysis: (id) => api.get(`/leads/${id}/analysis/`),
  updateAnalysis: (id, data) => api.patch(`/leads/${id}/analysis/`, data),
  update: (id, data) => api.patch(`/leads/${id}/`, data),
  apply: (id) => api.post(`/leads/${id}/apply/`),
  delete: (id) => api.delete(`/leads/${id}/`),
};

export const activityAPI = {
  getAll: () => api.get('/activity/'),
};

export const integrationsAPI = {
  getAll: () => api.get('/integrations/'),
};

export default api;
