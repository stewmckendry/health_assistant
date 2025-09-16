'use client';

import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';

const SESSION_STORAGE_KEY = 'health_assistant_session';
const USER_STORAGE_KEY = 'health_assistant_user';

interface SessionData {
  sessionId: string;
  userId: string;
  createdAt: string;
}

export function useSession() {
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initSession = async () => {
      try {
        // Check for existing session in localStorage
        const storedSession = localStorage.getItem(SESSION_STORAGE_KEY);
        const storedUser = localStorage.getItem(USER_STORAGE_KEY);

        if (storedSession) {
          // Parse and validate stored session
          const parsedSession = JSON.parse(storedSession);
          const sessionAge = Date.now() - new Date(parsedSession.createdAt).getTime();
          
          // Session expires after 24 hours
          if (sessionAge < 24 * 60 * 60 * 1000) {
            setSessionData(parsedSession);
            setIsLoading(false);
            return;
          }
        }

        // Create new session
        const userId = storedUser || `user_${uuidv4()}`;
        const response = await fetch('/api/sessions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ userId }),
        });

        if (!response.ok) {
          throw new Error('Failed to create session');
        }

        const data = await response.json();
        const newSession: SessionData = {
          sessionId: data.sessionId,
          userId: data.userId,
          createdAt: data.createdAt,
        };

        // Store in localStorage
        localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(newSession));
        localStorage.setItem(USER_STORAGE_KEY, userId);

        setSessionData(newSession);
      } catch (error) {
        console.error('Session initialization error:', error);
        
        // Fallback to local session
        const fallbackSession: SessionData = {
          sessionId: uuidv4(),
          userId: `user_${uuidv4()}`,
          createdAt: new Date().toISOString(),
        };
        
        setSessionData(fallbackSession);
      } finally {
        setIsLoading(false);
      }
    };

    initSession();
  }, []);

  const createNewSession = async () => {
    try {
      setIsLoading(true);
      
      const userId = sessionData?.userId || `user_${uuidv4()}`;
      const response = await fetch('/api/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ userId }),
      });

      if (!response.ok) {
        throw new Error('Failed to create new session');
      }

      const data = await response.json();
      const newSession: SessionData = {
        sessionId: data.sessionId,
        userId: data.userId,
        createdAt: data.createdAt,
      };

      // Update localStorage
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(newSession));
      setSessionData(newSession);
      
      // Reload page to reset chat
      window.location.reload();
    } catch (error) {
      console.error('Create new session error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    sessionId: sessionData?.sessionId,
    userId: sessionData?.userId,
    isLoading,
    createNewSession,
  };
}