'use client';

import { Box, Typography, Modal, IconButton, Divider, Grid, alpha } from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Activity, Zap, Database, HardDrive, Layers } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, PieChart, Pie, Cell } from 'recharts';
import { ServiceHealth } from '@/types';
import { LangSmithTrace, RerankerStats } from '@/types/observability';
import { DatabaseStats } from '@/hooks/useObservability';
import { HealthIndicator } from './HealthIndicator';
import { glassStyle } from '@/theme/theme';

interface DetailModalProps {
  open: boolean;
  onClose: () => void;
  serviceHealth: ServiceHealth[];
  langSmithTraces: LangSmithTrace[];
  rerankerStats: RerankerStats | null;
  databaseStats: DatabaseStats | null;
}

const COLORS = ['#14b8a6', '#8b5cf6', '#f59e0b', '#64748b'];

export function DetailModal({
  open,
  onClose,
  serviceHealth,
  langSmithTraces,
  rerankerStats,
  databaseStats,
}: DetailModalProps) {
  // Calculate totals for traces
  const totalTokens = langSmithTraces.reduce((sum, t) => sum + (t.tokenUsage?.total || 0), 0);
  const avgLatency = langSmithTraces.length > 0
    ? Math.round(langSmithTraces.reduce((sum, t) => sum + t.latencyMs, 0) / langSmithTraces.length)
    : 0;
  const errorCount = langSmithTraces.filter(t => t.status === 'error').length;

  // Prepare reranker cache data for pie chart
  const cacheData = rerankerStats ? [
    { name: 'Hits', value: rerankerStats.cache_hits, color: '#14b8a6' },
    { name: 'Misses', value: rerankerStats.cache_misses, color: '#f59e0b' },
  ] : [];

  // Prepare database pool data for bar chart
  const poolData = databaseStats ? [
    { name: 'Active', value: databaseStats.active_connections || 0 },
    { name: 'Pool Out', value: databaseStats.pool_checked_out || 0 },
    { name: 'Pool In', value: databaseStats.pool_checked_in || 0 },
    { name: 'Queue', value: databaseStats.queue_size || 0 },
  ] : [];

  // Queue stats for display
  const queueStats = databaseStats?.queue_stats || { queued: 0, processed: 0, failed: 0, retries: 0 };

  return (
    <Modal open={open} onClose={onClose}>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '90%',
              maxWidth: 900,
              maxHeight: '90vh',
              overflow: 'auto',
            }}
          >
            <Box
              sx={{
                borderRadius: '20px',
                p: 3,
                ...glassStyle,
                bgcolor: 'background.paper',
              }}
            >
              {/* Header */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 600 }}>
                    System Observability
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Real-time infrastructure metrics and traces
                  </Typography>
                </Box>
                <IconButton onClick={onClose}>
                  <X size={20} />
                </IconButton>
              </Box>

              {/* Service Health Row */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
                  Service Health
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {serviceHealth.map((service, idx) => (
                    <HealthIndicator key={idx} service={service} />
                  ))}
                </Box>
              </Box>

              <Divider sx={{ mb: 3 }} />

              <Grid container spacing={3}>
                {/* Reranker Cache Stats */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: (theme) => alpha(theme.palette.common.white, 0.02),
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <Layers size={16} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        Reranker Cache
                      </Typography>
                    </Box>
                    {rerankerStats ? (
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <ResponsiveContainer width={120} height={120}>
                          <PieChart>
                            <Pie
                              data={cacheData}
                              dataKey="value"
                              nameKey="name"
                              cx="50%"
                              cy="50%"
                              innerRadius={35}
                              outerRadius={50}
                            >
                              {cacheData.map((entry) => (
                                <Cell key={entry.name} fill={entry.color} />
                              ))}
                            </Pie>
                          </PieChart>
                        </ResponsiveContainer>
                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                            <Box sx={{ width: 8, height: 8, borderRadius: '2px', bgcolor: '#14b8a6' }} />
                            <Typography variant="caption" sx={{ flex: 1 }}>Cache Hits</Typography>
                            <Typography variant="caption" sx={{ fontWeight: 600 }}>{rerankerStats.cache_hits}</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                            <Box sx={{ width: 8, height: 8, borderRadius: '2px', bgcolor: '#f59e0b' }} />
                            <Typography variant="caption" sx={{ flex: 1 }}>Cache Misses</Typography>
                            <Typography variant="caption" sx={{ fontWeight: 600 }}>{rerankerStats.cache_misses}</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                            <Typography variant="caption" sx={{ flex: 1 }}>Cache Size</Typography>
                            <Typography variant="caption" sx={{ fontWeight: 600 }}>{rerankerStats.cache_size} items</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="caption" sx={{ flex: 1 }}>Model</Typography>
                            <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.65rem' }}>{rerankerStats.model_name.split('/').pop()}</Typography>
                          </Box>
                        </Box>
                      </Box>
                    ) : (
                      <Typography variant="caption" color="text.secondary">No reranker data available</Typography>
                    )}
                  </Box>
                </Grid>

                {/* Database Pool Stats */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: (theme) => alpha(theme.palette.common.white, 0.02),
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <HardDrive size={16} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        Database Pool
                      </Typography>
                    </Box>
                    {databaseStats ? (
                      <ResponsiveContainer width="100%" height={140}>
                        <BarChart data={poolData}>
                          <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip
                            contentStyle={{
                              background: '#1a1a24',
                              border: '1px solid rgba(255,255,255,0.1)',
                              borderRadius: 8,
                            }}
                          />
                          <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <Typography variant="caption" color="text.secondary">No database data available</Typography>
                    )}
                  </Box>
                </Grid>

                {/* Queue Processing Stats */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: (theme) => alpha(theme.palette.common.white, 0.02),
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <Database size={16} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        Queue Processing
                      </Typography>
                    </Box>
                    <Grid container spacing={2}>
                      <Grid size={{ xs: 3 }}>
                        <Typography variant="caption" color="text.secondary">Queued</Typography>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>{queueStats.queued}</Typography>
                      </Grid>
                      <Grid size={{ xs: 3 }}>
                        <Typography variant="caption" color="text.secondary">Processed</Typography>
                        <Typography variant="h6" sx={{ fontWeight: 600, color: 'success.main' }}>{queueStats.processed}</Typography>
                      </Grid>
                      <Grid size={{ xs: 3 }}>
                        <Typography variant="caption" color="text.secondary">Failed</Typography>
                        <Typography variant="h6" sx={{ fontWeight: 600, color: queueStats.failed > 0 ? 'error.main' : 'text.primary' }}>
                          {queueStats.failed}
                        </Typography>
                      </Grid>
                      <Grid size={{ xs: 3 }}>
                        <Typography variant="caption" color="text.secondary">Retries</Typography>
                        <Typography variant="h6" sx={{ fontWeight: 600, color: queueStats.retries > 0 ? 'warning.main' : 'text.primary' }}>
                          {queueStats.retries}
                        </Typography>
                      </Grid>
                    </Grid>
                  </Box>
                </Grid>

                {/* LangSmith Traces */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: (theme) => alpha(theme.palette.common.white, 0.02),
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <Activity size={16} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        LangSmith Traces
                      </Typography>
                    </Box>
                    {langSmithTraces.length > 0 ? (
                      <Grid container spacing={2}>
                        <Grid size={{ xs: 4 }}>
                          <Typography variant="caption" color="text.secondary">Total</Typography>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>{langSmithTraces.length}</Typography>
                        </Grid>
                        <Grid size={{ xs: 4 }}>
                          <Typography variant="caption" color="text.secondary">Avg Latency</Typography>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>{avgLatency}ms</Typography>
                        </Grid>
                        <Grid size={{ xs: 4 }}>
                          <Typography variant="caption" color="text.secondary">Errors</Typography>
                          <Typography variant="h6" sx={{ fontWeight: 600, color: errorCount > 0 ? 'error.main' : 'success.main' }}>
                            {errorCount}
                          </Typography>
                        </Grid>
                        {totalTokens > 0 && (
                          <Grid size={{ xs: 12 }}>
                            <Typography variant="caption" color="text.secondary">
                              Token Usage: {(totalTokens / 1000).toFixed(1)}K (~${((totalTokens / 1000) * 0.0015).toFixed(3)})
                            </Typography>
                          </Grid>
                        )}
                      </Grid>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        No traces available. Set LANGSMITH_API_KEY to enable tracing.
                      </Typography>
                    )}
                  </Box>
                </Grid>
              </Grid>
            </Box>
          </motion.div>
        )}
      </AnimatePresence>
    </Modal>
  );
}
