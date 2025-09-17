export interface Citation {
  url: string;
  title: string;
  snippet: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  timestamp: string;
  traceId?: string;
  guardrailTriggered?: boolean;
  error?: boolean;
  mode?: 'patient' | 'provider';  // Track mode for each message
  isStreaming?: boolean;  // Track streaming state
  metadata?: any;  // Additional metadata from streaming
}

export interface ChatSession {
  id: string;
  userId: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

export interface FeedbackData {
  traceId: string;
  sessionId: string;
  rating?: number;
  comment?: string;
  thumbsUp?: boolean;
}