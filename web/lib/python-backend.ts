const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export const pythonBackend = {
  async chat(data: {
    query: string;
    sessionId: string;
    userId?: string;
    mode?: string;
  }) {
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.statusText}`);
    }

    return response.json();
  },

  async submitFeedback(data: {
    traceId: string;
    sessionId: string;
    userId?: string;
    rating?: number;
    comment?: string;
    thumbsUp?: boolean;
  }) {
    const response = await fetch(`${BACKEND_URL}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.statusText}`);
    }

    return response.json();
  },

  async createSession(userId?: string) {
    const response = await fetch(`${BACKEND_URL}/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ userId }),
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.statusText}`);
    }

    return response.json();
  },

  async getSession(sessionId: string) {
    const response = await fetch(`${BACKEND_URL}/sessions/${sessionId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.statusText}`);
    }

    return response.json();
  },
};