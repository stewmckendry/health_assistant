/**
 * Session Manager for Multi-turn Conversations
 * Handles persistent conversation state using SQLite storage
 */

import Database from 'better-sqlite3';
import { ConversationSession, Message } from '@/types/agents';
import { v4 as uuidv4 } from 'uuid';
import { join } from 'path';

export class SessionManager {
  private db: Database.Database;
  private static instance: SessionManager;

  constructor(dbPath?: string) {
    const path = dbPath || join(process.cwd(), 'data', 'sessions.db');
    this.db = new Database(path);
    this.initializeDatabase();
  }

  static getInstance(dbPath?: string): SessionManager {
    if (!SessionManager.instance) {
      SessionManager.instance = new SessionManager(dbPath);
    }
    return SessionManager.instance;
  }

  private initializeDatabase(): void {
    // Create sessions table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        user_id TEXT,
        started_at TEXT NOT NULL,
        last_message_at TEXT NOT NULL,
        message_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        metadata TEXT DEFAULT '{}'
      )
    `);

    // Create messages table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        tool_calls TEXT DEFAULT '[]',
        citations TEXT DEFAULT '[]',
        metadata TEXT DEFAULT '{}',
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
      )
    `);

    // Create indexes for better performance
    this.db.exec(`
      CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON sessions(agent_id);
      CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
      CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
      CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
      CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
    `);
  }

  /**
   * Create a new conversation session
   */
  createSession(agentId: string, userId?: string): ConversationSession {
    const sessionId = uuidv4();
    const now = new Date().toISOString();

    const session: ConversationSession = {
      sessionId,
      agentId,
      userId,
      startedAt: now,
      lastMessageAt: now,
      messageCount: 0,
      status: 'active'
    };

    const stmt = this.db.prepare(`
      INSERT INTO sessions (session_id, agent_id, user_id, started_at, last_message_at, message_count, status)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      session.sessionId,
      session.agentId,
      session.userId || null,
      session.startedAt,
      session.lastMessageAt,
      session.messageCount,
      session.status
    );

    return session;
  }

  /**
   * Get session by ID
   */
  getSession(sessionId: string): ConversationSession | null {
    const stmt = this.db.prepare(`
      SELECT * FROM sessions WHERE session_id = ?
    `);

    const row = stmt.get(sessionId) as any;
    if (!row) return null;

    return {
      sessionId: row.session_id,
      agentId: row.agent_id,
      userId: row.user_id,
      startedAt: row.started_at,
      lastMessageAt: row.last_message_at,
      messageCount: row.message_count,
      status: row.status
    };
  }

  /**
   * Update session last activity
   */
  updateSessionActivity(sessionId: string): void {
    const stmt = this.db.prepare(`
      UPDATE sessions 
      SET last_message_at = ?, message_count = message_count + 1
      WHERE session_id = ?
    `);

    stmt.run(new Date().toISOString(), sessionId);
  }

  /**
   * Add message to session
   */
  addMessage(message: Message): void {
    const stmt = this.db.prepare(`
      INSERT INTO messages (id, session_id, role, content, timestamp, tool_calls, citations, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      message.id,
      message.sessionId,
      message.role,
      message.content,
      message.timestamp,
      JSON.stringify(message.toolCalls || []),
      JSON.stringify(message.citations || []),
      JSON.stringify({ streaming: message.streaming, error: message.error })
    );

    this.updateSessionActivity(message.sessionId);
  }

  /**
   * Get conversation history for a session
   */
  getConversationHistory(sessionId: string, limit = 50): Message[] {
    const stmt = this.db.prepare(`
      SELECT * FROM messages 
      WHERE session_id = ? 
      ORDER BY timestamp DESC 
      LIMIT ?
    `);

    const rows = stmt.all(sessionId, limit) as any[];
    
    return rows.reverse().map(row => ({
      id: row.id,
      sessionId: row.session_id,
      role: row.role,
      content: row.content,
      timestamp: row.timestamp,
      toolCalls: JSON.parse(row.tool_calls || '[]'),
      citations: JSON.parse(row.citations || '[]'),
      streaming: JSON.parse(row.metadata || '{}').streaming,
      error: JSON.parse(row.metadata || '{}').error
    }));
  }

  /**
   * Get recent sessions for a user
   */
  getUserSessions(userId: string, limit = 10): ConversationSession[] {
    const stmt = this.db.prepare(`
      SELECT * FROM sessions 
      WHERE user_id = ? 
      ORDER BY last_message_at DESC 
      LIMIT ?
    `);

    const rows = stmt.all(userId, limit) as any[];
    
    return rows.map(row => ({
      sessionId: row.session_id,
      agentId: row.agent_id,
      userId: row.user_id,
      startedAt: row.started_at,
      lastMessageAt: row.last_message_at,
      messageCount: row.message_count,
      status: row.status
    }));
  }

  /**
   * End a session
   */
  endSession(sessionId: string): void {
    const stmt = this.db.prepare(`
      UPDATE sessions 
      SET status = 'ended' 
      WHERE session_id = ?
    `);

    stmt.run(sessionId);
  }

  /**
   * Clean up old sessions
   */
  cleanupOldSessions(olderThanDays = 30): number {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);

    const deleteMessages = this.db.prepare(`
      DELETE FROM messages 
      WHERE session_id IN (
        SELECT session_id FROM sessions 
        WHERE last_message_at < ?
      )
    `);

    const deleteSessions = this.db.prepare(`
      DELETE FROM sessions 
      WHERE last_message_at < ?
    `);

    this.db.transaction(() => {
      deleteMessages.run(cutoffDate.toISOString());
      deleteSessions.run(cutoffDate.toISOString());
    })();

    return deleteSessions.changes;
  }

  /**
   * Get session statistics
   */
  getSessionStats(agentId?: string): {
    totalSessions: number;
    activeSessions: number;
    totalMessages: number;
    averageMessagesPerSession: number;
  } {
    let sessionQuery = 'SELECT COUNT(*) as total, COUNT(CASE WHEN status = "active" THEN 1 END) as active FROM sessions';
    let messageQuery = 'SELECT COUNT(*) as total FROM messages';
    
    const params: any[] = [];
    if (agentId) {
      sessionQuery += ' WHERE agent_id = ?';
      messageQuery += ' WHERE session_id IN (SELECT session_id FROM sessions WHERE agent_id = ?)';
      params.push(agentId);
    }

    const sessionStats = this.db.prepare(sessionQuery).get(...params) as any;
    const messageStats = this.db.prepare(messageQuery).get(...params) as any;

    return {
      totalSessions: sessionStats.total,
      activeSessions: sessionStats.active,
      totalMessages: messageStats.total,
      averageMessagesPerSession: sessionStats.total > 0 ? messageStats.total / sessionStats.total : 0
    };
  }

  /**
   * Close database connection
   */
  close(): void {
    this.db.close();
  }
}