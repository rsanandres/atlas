'use client';

import { useState, useCallback, useRef } from 'react';
import { PipelineStep, Message } from '@/types';

// Timing tracker for pipeline steps
interface StepTiming {
  startTime?: number;
  endTime?: number;
}

// Default pipeline steps that match the RAG workflow
const DEFAULT_PIPELINE: PipelineStep[] = [
  {
    id: 'query',
    name: 'Query Input',
    description: 'User query received',
    status: 'pending',
  },
  {
    id: 'pii_mask',
    name: 'PII Masking',
    description: 'Scrubbing sensitive data with AWS Comprehend Medical',
    status: 'pending',
  },
  {
    id: 'vector_search',
    name: 'Vector Search',
    description: 'Searching pgvector for relevant documents',
    status: 'pending',
  },
  {
    id: 'rerank',
    name: 'Reranking',
    description: 'Cross-encoder reranking for precision',
    status: 'pending',
  },
  {
    id: 'llm_react',
    name: 'LLM ReAct',
    description: 'Claude 3.5 Haiku reasoning with tools',
    status: 'pending',
  },
  {
    id: 'response',
    name: 'Response',
    description: 'Final response with PII masking',
    status: 'pending',
  },
];

// Map tool calls to pipeline steps
const TOOL_TO_STEP: Record<string, string[]> = {
  search_clinical_notes: ['vector_search', 'rerank'],
  get_patient_timeline: ['vector_search', 'rerank'],
  cross_reference_meds: ['llm_react'],
  get_session_context: ['llm_react'],
  calculate: ['llm_react'],
  get_current_date: ['llm_react'],
};

export function useWorkflow() {
  const [pipeline, setPipeline] = useState<PipelineStep[]>(DEFAULT_PIPELINE);
  const [lastToolCalls, setLastToolCalls] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  // Track timing for each step
  const stepTimings = useRef<Record<string, StepTiming>>({});
  const processingStartTime = useRef<number>(0);

  // Reset pipeline to pending state
  const resetPipeline = useCallback(() => {
    setPipeline(DEFAULT_PIPELINE.map(step => ({ ...step, status: 'pending', details: undefined })));
    setLastToolCalls([]);
    stepTimings.current = {};
  }, []);

  // Simulate pipeline progress when processing
  const startProcessing = useCallback(() => {
    setIsProcessing(true);
    resetPipeline();
    processingStartTime.current = Date.now();

    // Animate through steps with timing
    const steps = ['query', 'pii_mask', 'vector_search', 'rerank', 'llm_react'];
    let currentIndex = 0;

    const interval = setInterval(() => {
      if (currentIndex < steps.length) {
        const stepId = steps[currentIndex];
        const now = Date.now();

        // Mark previous step as completed with timing
        if (currentIndex > 0) {
          const prevStepId = steps[currentIndex - 1];
          stepTimings.current[prevStepId] = {
            ...stepTimings.current[prevStepId],
            endTime: now,
          };
        }

        // Start timing for current step
        stepTimings.current[stepId] = { startTime: now };

        setPipeline(prev => prev.map(step => {
          if (step.id === stepId) {
            return { ...step, status: 'active' };
          }
          if (steps.indexOf(step.id) < currentIndex) {
            const timing = stepTimings.current[step.id];
            const duration = timing?.startTime && timing?.endTime
              ? timing.endTime - timing.startTime
              : undefined;
            return { ...step, status: 'completed', duration };
          }
          return step;
        }));
        currentIndex++;
      } else {
        clearInterval(interval);
      }
    }, 400);

    return () => clearInterval(interval);
  }, [resetPipeline]);

  // Update pipeline based on response
  const updateFromResponse = useCallback((response: Message | null) => {
    if (!response) return;

    const endTime = Date.now();
    const totalLatency = processingStartTime.current
      ? endTime - processingStartTime.current
      : 0;

    setIsProcessing(false);
    const toolCalls = response.toolCalls || [];
    const sources = response.sources || [];
    setLastToolCalls(toolCalls);

    // Determine which steps were actually used
    const usedSteps = new Set<string>(['query', 'pii_mask', 'response']);

    // Add steps based on tool calls
    toolCalls.forEach(tool => {
      const steps = TOOL_TO_STEP[tool];
      if (steps) {
        steps.forEach(step => usedSteps.add(step));
      }
    });

    // If any search tool was called, mark vector_search and rerank as completed
    if (toolCalls.some(t => t.includes('search') || t.includes('timeline'))) {
      usedSteps.add('vector_search');
      usedSteps.add('rerank');
    }

    // Always mark llm_react as used (LLM always runs)
    usedSteps.add('llm_react');

    // Calculate details for each step based on available data
    const stepDetails: Record<string, Record<string, unknown>> = {
      query: {
        // Query details are passed via queryText prop
      },
      pii_mask: {
        // PII masking details - would need backend to emit these
        entitiesFound: 0,
        namesMasked: 0,
        idsMasked: 0,
        datesMasked: 0,
        processingTime: 0,
      },
      vector_search: {
        docsRetrieved: sources.length,
        searchTime: 0, // Would need backend timing
      },
      rerank: {
        candidatesIn: sources.length > 0 ? Math.min(sources.length * 2, 20) : 0,
        resultsOut: sources.length,
        topScore: sources.length > 0 ? 0.85 : 0, // Would need actual scores
        rerankTime: 0,
      },
      llm_react: {
        inputTokens: 0, // Would need backend to emit
        outputTokens: 0,
        reasoningSteps: toolCalls.length > 0 ? toolCalls.length : 1,
        toolsInvoked: toolCalls.length,
        latency: Math.round(totalLatency * 0.7), // Estimate LLM takes ~70% of time
      },
      response: {
        responseLength: response.content?.length || 0,
        sourcesCited: sources.length,
        piiRemasked: 0,
        totalLatency: totalLatency,
      },
    };

    setPipeline(prev => prev.map(step => ({
      ...step,
      status: usedSteps.has(step.id) ? 'completed' : 'skipped',
      details: stepDetails[step.id],
      duration: step.id === 'response' ? totalLatency : undefined,
    })));
  }, []);

  return {
    pipeline,
    lastToolCalls,
    isProcessing,
    resetPipeline,
    startProcessing,
    updateFromResponse,
  };
}
