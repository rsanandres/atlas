'use client';

import { useState, useCallback, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Message, AgentQueryResponse } from '@/types';
import { queryAgent } from '@/services/agentApi';
import { useSessions } from './useSessions';
import { useUser } from './useUser';

export function useChat(sessionId?: string) {
  const { userId } = useUser();
  const { activeSessionId, loadSessionMessages, updateSession, createNewSession } = useSessions();
  const effectiveSessionId = sessionId || activeSessionId;
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageCount, setMessageCount] = useState<number>(0);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const loadMessagesForSession = useCallback(async (sid: string) => {
    if (!sid) {
      console.log('[useChat] No session ID provided, skipping message load');
      return;
    }
    
    console.log('[useChat] Loading messages for session:', sid);
    setIsLoadingMessages(true);
    try {
      const sessionMessages = await loadSessionMessages(sid, 50);
      console.log('[useChat] Loaded session messages:', sessionMessages.length, sessionMessages);
      
      // Convert session turns to Message format
      const convertedMessages: Message[] = sessionMessages
        .sort((a: any, b: any) => {
          // Sort by turn_ts (oldest first)
          return (a.turn_ts || '').localeCompare(b.turn_ts || '');
        })
        .map((turn: any) => ({
          id: turn.turn_ts || uuidv4(),
          role: turn.role === 'user' ? 'user' : 'assistant',
          content: turn.text || '',
          timestamp: new Date(turn.turn_ts || Date.now()),
          sources: turn.meta?.sources,
          toolCalls: turn.meta?.tool_calls,
          researcherOutput: turn.meta?.researcher_output,
          validatorOutput: turn.meta?.validator_output,
          validationResult: turn.meta?.validation_result,
        }));
      
      console.log('[useChat] Converted messages:', convertedMessages.length, convertedMessages);
      setMessages(convertedMessages);
      setMessageCount(convertedMessages.filter(m => m.role === 'user').length);
    } catch (err) {
      console.error('[useChat] Failed to load messages:', err);
      // Don't clear messages on error, just log it
      // setMessages([]);
    } finally {
      setIsLoadingMessages(false);
    }
  }, [loadSessionMessages]);

  // Load messages when session changes
  useEffect(() => {
    if (effectiveSessionId) {
      loadMessagesForSession(effectiveSessionId);
    } else {
      // If no session, clear messages but don't prevent sending
      // (a session will be created when first message is sent)
      setMessages([]);
      setMessageCount(0);
    }
  }, [effectiveSessionId, loadMessagesForSession]);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Check agent service health before sending message
    try {
      const healthUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/agent/health`;
      const healthController = new AbortController();
      const healthTimeout = setTimeout(() => healthController.abort(), 3000);
      
      const healthResponse = await fetch(healthUrl, {
        signal: healthController.signal,
      });
      
      clearTimeout(healthTimeout);
      
      if (!healthResponse.ok) {
        throw new Error(`Service health check failed: ${healthResponse.status}`);
      }
    } catch (healthError) {
      const errorMsg = 'Agent service is unavailable. Please ensure the backend service is running.';
      console.error('[useChat] Service health check failed:', {
        error: healthError instanceof Error ? healthError.message : String(healthError),
        stack: healthError instanceof Error ? healthError.stack : undefined,
      });
      setError(errorMsg);
      return;
    }

    // If no session, create one first
    let sessionId = effectiveSessionId;
    if (!sessionId && userId) {
      try {
        const newSession = await createNewSession();
        if (newSession) {
          sessionId = newSession.session_id;
        } else {
          setError('Failed to create session. Please try again.');
          return;
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to create session. Please try again.';
        console.error('[useChat] Failed to create session:', err);
        setError(errorMessage);
        return;
      }
    }

    if (!sessionId) {
      setError('No session available. Please wait...');
      return;
    }

    setError(null);
    
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    };

    // Add user message and loading placeholder
    const loadingMessage: Message = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages(prev => [...prev, userMessage, loadingMessage]);
    setIsLoading(true);
    setMessageCount(prev => prev + 1);

    try {
      const response: AgentQueryResponse = await queryAgent({
        query: content.trim(),
        session_id: sessionId,
        user_id: userId,
      });

      const assistantMessage: Message = {
        id: loadingMessage.id,
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        sources: response.sources,
        toolCalls: response.tool_calls,
        researcherOutput: response.researcher_output,
        validatorOutput: response.validator_output,
        validationResult: response.validation_result,
      };

      setMessages(prev => 
        prev.map(m => m.id === loadingMessage.id ? assistantMessage : m)
      );

      // Auto-update session name from first message if session has no name
      if (messageCount === 0 && sessionId) {
        try {
          // Update session name from first message (truncate to 50 chars)
          const sessionName = content.trim().slice(0, 50);
          await updateSession(sessionId, { name: sessionName });
        } catch (err) {
          // Ignore errors in name update
          console.warn('Failed to update session name:', err);
        }
      }

      // Don't reload messages here - we already updated the local state
      // Reloading would cause a flash and potential race condition
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get response';
      setError(errorMessage);
      
      // Update loading message to show error
      setMessages(prev => 
        prev.map(m => m.id === loadingMessage.id ? {
          ...m,
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          isLoading: false,
        } : m)
      );
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, effectiveSessionId, userId, messageCount, updateSession, createNewSession]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setMessageCount(0);
    // Note: Session clearing is handled by useSessions hook
  }, []);

  const getLastResponse = useCallback((): Message | null => {
    const assistantMessages = messages.filter(m => m.role === 'assistant' && !m.isLoading);
    return assistantMessages[assistantMessages.length - 1] || null;
  }, [messages]);

  return {
    messages,
    isLoading: isLoading || isLoadingMessages,
    error,
    sessionId: effectiveSessionId,
    messageCount,
    sendMessage,
    clearChat,
    getLastResponse,
  };
}
