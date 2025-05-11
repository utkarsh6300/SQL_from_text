const API_BASE_URL = 'http://localhost:5000/api';

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

const handleResponse = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({
      message: 'An unexpected error occurred'
    }));
    throw new ApiError(error.message || 'An unexpected error occurred', response.status);
  }
  return response.json();
};

export const projectApi = {
  async createProject(projectData) {
    const response = await fetch(`${API_BASE_URL}/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(projectData),
    });
    return handleResponse(response);
  },

  async getProjects() {
    const response = await fetch(`${API_BASE_URL}/projects`);
    return handleResponse(response);
  },

  async getProject(projectId) {
    const response = await fetch(`${API_BASE_URL}/projects/${projectId}`);
    return handleResponse(response);
  },

  async addSampleQuery(projectId, query) {
    const response = await fetch(`${API_BASE_URL}/projects/${projectId}/samples`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(query),
    });
    return handleResponse(response);
  },
};

export const chatApi = {
  async getChats(projectId) {
    const response = await fetch(`${API_BASE_URL}/projects/${projectId}/chats`);
    return handleResponse(response);
  },

  async createChat(projectId) {
    const response = await fetch(`${API_BASE_URL}/projects/${projectId}/chats`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  async generateSql(projectId, chatId, text) {
    const response = await fetch(`${API_BASE_URL}/projects/${projectId}/chats/${chatId}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });
    return handleResponse(response);
  },

  async regenerateSql(projectId, chatId, messageId) {
    const response = await fetch(
      `${API_BASE_URL}/projects/${projectId}/chats/${chatId}/messages/${messageId}/regenerate`,
      { method: 'POST' }
    );
    return handleResponse(response);
  },
};