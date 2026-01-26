'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getAgentHealth,
  getRerankerHealth,
  getRerankerStats,
  getLangSmithTraces,
  getEmbeddingsHealth,
} from '@/services/agentApi';
import { CloudWatchMetric, LangSmithTrace, MetricSummary, RerankerStats, CostBreakdown } from '@/types/observability';
import { ServiceHealth } from '@/types';

const REFRESH_INTERVAL = 5000; // 5 seconds for real-time updates

// Initial data (empty, will be populated by first fetch)
function getInitialData() {
  return {
    cloudWatchMetrics: [] as CloudWatchMetric[],
    langSmithTraces: [] as LangSmithTrace[],
    rerankerStats: null as RerankerStats | null,
    serviceHealth: [] as ServiceHealth[],
    metricSummaries: [] as MetricSummary[],
    costBreakdown: [] as CostBreakdown[],
  };
}

export function useObservability() {
  // Initialize with data to avoid calling setState in effect
  const [data, setData] = useState(getInitialData);
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const refreshData = useCallback(async () => {
    setIsLoading(true);
    
    try {
      // Fetch all service health checks in parallel (graceful degradation)
      const [agentHealth, rerankerHealth, embeddingsHealth, rerankerStats, langSmithTraces] = await Promise.allSettled([
        getAgentHealth(),
        getRerankerHealth(),
        getEmbeddingsHealth(),
        getRerankerStats(),
        getLangSmithTraces(10),
      ]);

      // Build service health array (handle failures gracefully)
      const serviceHealth: ServiceHealth[] = [];
      if (agentHealth.status === 'fulfilled') {
        serviceHealth.push(agentHealth.value);
      } else {
        console.error('Agent health check failed:', agentHealth.reason);
        // Still add unhealthy status so it shows in UI
        serviceHealth.push({
          name: 'Agent Service',
          status: 'unhealthy',
          lastChecked: new Date(),
        });
      }
      if (rerankerHealth.status === 'fulfilled') {
        serviceHealth.push(rerankerHealth.value);
      } else {
        console.error('Reranker health check failed:', rerankerHealth.reason);
        serviceHealth.push({
          name: 'Reranker Service',
          status: 'unhealthy',
          lastChecked: new Date(),
        });
      }
      if (embeddingsHealth.status === 'fulfilled') {
        serviceHealth.push(embeddingsHealth.value);
      } else {
        console.error('Embeddings health check failed:', embeddingsHealth.reason);
        serviceHealth.push({
          name: 'Embeddings Service',
          status: 'unhealthy',
          lastChecked: new Date(),
        });
      }

      // Get reranker stats (null if failed)
      const stats = rerankerStats.status === 'fulfilled' ? rerankerStats.value : null;

      // Get LangSmith traces (empty array if failed or no API key)
      const traces = langSmithTraces.status === 'fulfilled' ? langSmithTraces.value : [];

      // Calculate metric summaries from available data
      const metricSummaries: MetricSummary[] = [];
      if (stats) {
        const totalRequests = stats.cache_hits + stats.cache_misses;
        const hitRate = totalRequests > 0 ? (stats.cache_hits / totalRequests) * 100 : 0;
        
        metricSummaries.push(
          {
            label: 'Cache Hit Rate',
            value: `${hitRate.toFixed(1)}%`,
            unit: '%',
          },
          {
            label: 'Cache Size',
            value: stats.cache_size,
            unit: 'items',
          },
          {
            label: 'Total Requests',
            value: totalRequests,
            unit: 'requests',
          }
        );
      }

      // Calculate cost breakdown (placeholder - would need actual cost data)
      const costBreakdown: CostBreakdown[] = [];

      // CloudWatch metrics (placeholder - would need actual CloudWatch integration)
      const cloudWatchMetrics: CloudWatchMetric[] = [];

      setData({
        cloudWatchMetrics,
        langSmithTraces: traces,
        rerankerStats: stats,
        serviceHealth,
        metricSummaries,
        costBreakdown,
      });
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Error refreshing observability data:', error);
      // Keep existing data on error (graceful degradation)
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial data fetch
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(refreshData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [refreshData]);

  // Get metrics by namespace
  const getMetricsByNamespace = useCallback((namespace: string) => {
    return data.cloudWatchMetrics.filter(m => m.namespace === namespace);
  }, [data.cloudWatchMetrics]);

  // Get overall health status
  const getOverallHealth = useCallback((): 'healthy' | 'degraded' | 'unhealthy' => {
    if (data.serviceHealth.some(s => s.status === 'unhealthy')) return 'unhealthy';
    if (data.serviceHealth.some(s => s.status === 'degraded')) return 'degraded';
    return 'healthy';
  }, [data.serviceHealth]);

  // Calculate cache hit rate
  const getCacheHitRate = useCallback((): number => {
    if (!data.rerankerStats) return 0;
    const total = data.rerankerStats.cache_hits + data.rerankerStats.cache_misses;
    return total > 0 ? (data.rerankerStats.cache_hits / total) * 100 : 0;
  }, [data.rerankerStats]);

  // Get total estimated cost
  const getTotalCost = useCallback((): number => {
    return data.costBreakdown.reduce((sum, item) => sum + item.cost, 0);
  }, [data.costBreakdown]);

  return {
    cloudWatchMetrics: data.cloudWatchMetrics,
    langSmithTraces: data.langSmithTraces,
    rerankerStats: data.rerankerStats,
    serviceHealth: data.serviceHealth,
    metricSummaries: data.metricSummaries,
    costBreakdown: data.costBreakdown,
    isLoading,
    lastUpdated,
    refreshData,
    getMetricsByNamespace,
    getOverallHealth,
    getCacheHitRate,
    getTotalCost,
  };
}
