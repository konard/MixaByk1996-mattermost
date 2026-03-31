const API_URL = '/api';

async function request(endpoint, options = {}) {
  const url = `${API_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const token = localStorage.getItem('authToken');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export const api = {
  // User endpoints
  getUser: (userId) => request(`/users/${userId}/`),

  getUserByPlatform: (platform, platformUserId) =>
    request(`/users/by_platform/?platform=${platform}&platform_user_id=${platformUserId}`),

  registerUser: (data) =>
    request('/users/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateUser: (userId, data) =>
    request(`/users/${userId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  getUserBalance: (userId) => request(`/users/${userId}/balance/`),

  // Procurement endpoints
  getProcurements: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/procurements/?${query}`);
  },

  getProcurement: (id) => request(`/procurements/${id}/`),

  createProcurement: (data) =>
    request('/procurements/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  joinProcurement: (id, data) =>
    request(`/procurements/${id}/join/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  leaveProcurement: (id) =>
    request(`/procurements/${id}/leave/`, {
      method: 'POST',
    }),

  getUserProcurements: (userId) => request(`/procurements/user/${userId}/`),

  getCategories: () => request('/procurements/categories/'),

  // Chat endpoints
  getMessages: (procurementId, params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/chat/messages/?procurement=${procurementId}&${query}`);
  },

  sendMessage: (data) =>
    request('/chat/messages/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getNotifications: (userId) => request(`/chat/notifications/?user=${userId}`),

  // Payment endpoints
  createPayment: (data) =>
    request('/payments/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getPaymentStatus: (paymentId) => request(`/payments/${paymentId}/status/`),
};
