'use client';

import { useEffect, useState } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { WorkflowPanel } from '@/components/workflow/WorkflowPanel';
import { ObservabilityPanel } from '@/components/observability/ObservabilityPanel';
import { ConnectModal } from '@/components/lead-capture/ConnectModal';
import { SessionSidebar } from '@/components/session/SessionSidebar';
import { useChat } from '@/hooks/useChat';
import { useWorkflow } from '@/hooks/useWorkflow';
import { useObservability } from '@/hooks/useObservability';
import { useLeadCapture } from '@/hooks/useLeadCapture';
import { useSessions } from '@/hooks/useSessions';
import { getMockCostBreakdown } from '@/services/mockData';

export default function Home() {
  const { activeSessionId, switchSession } = useSessions();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { messages, isLoading, error, sendMessage, clearChat, getLastResponse, messageCount } = useChat();
  const { pipeline, lastToolCalls, isProcessing, startProcessing, updateFromResponse } = useWorkflow();
  const {
    serviceHealth,
    metricSummaries,
    cloudWatchMetrics,
    langSmithTraces,
    lastUpdated,
    refreshData,
    isLoading: obsLoading,
  } = useObservability();
  const { isOpen: leadOpen, dismiss: dismissLead } = useLeadCapture(messageCount);
  
  // Track the last query for workflow display
  const [lastQuery, setLastQuery] = useState<string>('');

  // Start workflow animation when sending a message
  const handleSend = (message: string) => {
    setLastQuery(message);
    startProcessing();
    sendMessage(message);
  };

  // Update workflow when response arrives
  useEffect(() => {
    if (!isLoading) {
      const lastResponse = getLastResponse();
      updateFromResponse(lastResponse);
    }
  }, [isLoading, getLastResponse, updateFromResponse]);

  // Get the last user message for workflow display (fallback to tracked query)
  const lastUserMessage = messages.filter(m => m.role === 'user').pop();
  const displayQuery = lastUserMessage?.content || lastQuery;

  const handleSessionSelect = (sessionId: string) => {
    switchSession(sessionId);
    setSidebarOpen(false);
  };

  return (
    <>
      <SessionSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onSessionSelect={handleSessionSelect}
      />
      <MainLayout
        chatPanel={
          <ChatPanel
            messages={messages}
            isLoading={isLoading}
            error={error}
            onSend={handleSend}
            onClear={clearChat}
            onOpenSessions={() => setSidebarOpen(true)}
          />
        }
        workflowPanel={
          <WorkflowPanel
            pipeline={pipeline}
            toolCalls={lastToolCalls}
            lastResponse={getLastResponse()}
            isProcessing={isProcessing}
            lastQuery={displayQuery}
          />
        }
        observabilityPanel={
          <ObservabilityPanel
            serviceHealth={serviceHealth}
            metricSummaries={metricSummaries}
            cloudWatchMetrics={cloudWatchMetrics}
            langSmithTraces={langSmithTraces}
            costBreakdown={getMockCostBreakdown()}
            lastUpdated={lastUpdated}
            onRefresh={refreshData}
            isLoading={obsLoading}
          />
        }
      />
      <ConnectModal
        open={leadOpen}
        onClose={dismissLead}
      />
    </>
  );
}
