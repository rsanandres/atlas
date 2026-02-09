import { ServiceHealth } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const HEALTH_CHECK_TIMEOUT = 30000; // 30 seconds for health checks (remote backend)

// Fetch with timeout
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = HEALTH_CHECK_TIMEOUT
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout}ms`);
    }
    throw error;
  }
}

export interface EmbeddingsHealth {
  status: 'healthy' | 'unhealthy';
  timestamp?: string;
}

export async function getEmbeddingsHealth(): Promise<ServiceHealth> {
  try {
    const start = Date.now();
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/embeddings/health`,
      {},
      HEALTH_CHECK_TIMEOUT
    );
    const latency = Date.now() - start;

    if (!response.ok) {
      return {
        name: 'Embeddings Service',
        status: 'unhealthy',
        latency,
        lastChecked: new Date(),
      };
    }

    return {
      name: 'Embeddings Service',
      status: 'healthy',
      latency,
      lastChecked: new Date(),
    };
  } catch {
    return {
      name: 'Embeddings Service',
      status: 'unhealthy',
      lastChecked: new Date(),
    };
  }
}
