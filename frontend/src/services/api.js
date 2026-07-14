import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

let csrfToken = null;

export async function fetchCSRFToken() {
  const response = await api.get('/csrf/');
  csrfToken = response.data.csrfToken;
  return csrfToken;
}

api.interceptors.request.use((config) => {
  if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method)) {
    config.headers['X-CSRFToken'] = csrfToken;
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
  create: (data) => api.post('/leads/', data),
  getById: (id) => api.get(`/leads/${id}/`),
  getAnalysis: (id) => api.get(`/leads/${id}/analysis/`),
  update: (id, data) => api.patch(`/leads/${id}/`, data),
  delete: (id) => api.delete(`/leads/${id}/`),
};

export const activityAPI = {
  getAll: () => api.get('/activity/'),
};

export const integrationsAPI = {
  getAll: () => api.get('/integrations/'),
};

export default api;
