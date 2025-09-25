/**
 * Type definitions for Clinical AI Agents Web Application
 */

/**
 * Agent status indicators
 */
export type AgentStatus = 'active' | 'coming-soon' | 'beta' | 'maintenance';

/**
 * Agent configuration and metadata
 */
export interface AgentInfo {
  id: string;
  name: string;
  description: string;
  fullDescription: string;
  mission: string;
  status: AgentStatus;
  icon: string;
  color: string;
  endpoint: string;
  tools: AgentTool[];
  knowledgeSources: KnowledgeSource[];
  capabilities: string[];
  limitations: string[];
  disclaimer?: string;
  launchDate?: string;
}

/**
 * MCP Tool information
 */
export interface AgentTool {
  name: string;
  description: string;
  category: 'search' | 'retrieval' | 'analysis' | 'validation';
  parameters?: Record<string, any>;
}

/**
 * Knowledge source information
 */
export interface KnowledgeSource {
  name: string;
  organization: string;
  type: 'regulatory' | 'clinical' | 'research' | 'educational';
  url?: string;
  lastUpdated?: string;
  documentCount?: number;
}

/**
 * Conversation session
 */
export interface ConversationSession {
  sessionId: string;
  agentId: string;
  userId?: string;
  startedAt: string;
  lastMessageAt: string;
  messageCount: number;
  status: 'active' | 'idle' | 'ended';
}

/**
 * Message in a conversation
 */
export interface Message {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  toolCalls?: ToolCall[];
  citations?: Citation[];
  streaming?: boolean;
  error?: string;
}

/**
 * Tool call information
 */
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  result?: any;
  error?: string;
}

/**
 * Citation from agent response
 */
export interface Citation {
  id: string;
  title: string;
  source: string;
  url: string;
  domain: string;
  isTrusted: boolean;
  snippet?: string;
  publishedDate?: string;
  accessDate: string;
}

/**
 * Streaming event types
 */
export type StreamEventType = 
  | 'text'
  | 'tool_call_start'
  | 'tool_call_end'
  | 'citation'
  | 'error'
  | 'done';

/**
 * Streaming event from SSE
 */
export interface StreamEvent {
  type: StreamEventType;
  data: any;
  timestamp: string;
}

/**
 * Text streaming event
 */
export interface TextStreamEvent extends StreamEvent {
  type: 'text';
  data: {
    content: string;
    delta: string;
  };
}

/**
 * Tool call streaming event
 */
export interface ToolCallStreamEvent extends StreamEvent {
  type: 'tool_call_start' | 'tool_call_end';
  data: ToolCall;
}

/**
 * Citation streaming event
 */
export interface CitationStreamEvent extends StreamEvent {
  type: 'citation';
  data: Citation;
}

/**
 * Agent response from API
 */
export interface AgentResponse {
  sessionId: string;
  messageId: string;
  content: string;
  toolCalls: ToolCall[];
  citations: Citation[];
  processingTime: number;
  tokensUsed?: number;
}

/**
 * Agent health check response
 */
export interface AgentHealthCheck {
  agentId: string;
  status: 'healthy' | 'degraded' | 'unavailable';
  lastChecked: string;
  components: {
    mcp: boolean;
    llm: boolean;
    knowledgeBase: boolean;
  };
  message?: string;
}

/**
 * Conversation history
 */
export interface ConversationHistory {
  sessionId: string;
  agentId: string;
  messages: Message[];
  metadata: {
    startedAt: string;
    lastMessageAt: string;
    totalMessages: number;
    totalToolCalls: number;
    totalCitations: number;
  };
}

/**
 * API Error response
 */
export interface ApiError {
  error: string;
  message: string;
  code?: string;
  details?: any;
}

/**
 * User preferences for agent interaction
 */
export interface UserPreferences {
  streamingEnabled: boolean;
  showToolCalls: boolean;
  autoExpandCitations: boolean;
  messageHistoryLimit: number;
  theme?: 'light' | 'dark' | 'system';
}

/**
 * Agent statistics
 */
export interface AgentStats {
  agentId: string;
  totalSessions: number;
  totalMessages: number;
  averageResponseTime: number;
  successRate: number;
  popularTools: Array<{ name: string; count: number }>;
  lastUsed: string;
}