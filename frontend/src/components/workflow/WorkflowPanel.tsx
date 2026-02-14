import { useState, useEffect } from 'react';
import { Box, Typography, Chip, Stack, Divider, alpha, Tabs, Tab, Skeleton } from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';
import { Workflow, Wrench, Info, Users } from 'lucide-react';
import { PipelineStep as PipelineStepType, Message } from '@/types';
import { PipelineStep } from './PipelineStep';
import { SourceCard } from './SourceCard';
import { ReferencePanel } from './ReferencePanel';
import { DocumentationPanel } from './DocumentationPanel';
import { glassStyle } from '@/theme/theme';

// Patient type for selection
interface SelectedPatient {
  id: string;
  name: string;
}

interface WorkflowPanelProps {
  pipeline: PipelineStepType[];
  toolCalls: string[];
  lastResponse: Message | null;
  isProcessing: boolean;
  lastQuery?: string;
  onPromptSelect?: (text: string) => void;
  selectedPatient?: SelectedPatient | null;
  onPatientSelect?: (patient: SelectedPatient | null) => void;
  referencePanelCollapsed?: boolean;
}

export function WorkflowPanel({ pipeline, toolCalls, lastResponse, isProcessing, lastQuery, onPromptSelect, selectedPatient, onPatientSelect, referencePanelCollapsed }: WorkflowPanelProps) {
  const [tabIndex, setTabIndex] = useState(0);

  // Switch to Pipeline tab when a prompt is sent (reference panel collapsed)
  useEffect(() => {
    if (referencePanelCollapsed) {
      setTabIndex(1);
    }
  }, [referencePanelCollapsed]);
  const sources = lastResponse?.sources || [];
  const hasActivity = pipeline.some(s => s.status === 'completed' || s.status === 'active');
  const hasCompletedSteps = pipeline.some(s => s.status === 'completed');

  const handleCopyFeedback = (msg: string) => {
    // Ideally we would show a snackbar here, but for now we trust the copy action
    console.log(msg);
  };

  return (
    <div style={{ height: '100%' }}>
      <Box
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: '16px',
          overflow: 'hidden',
          ...glassStyle,
        }}
      >
        {/* Header with Tabs */}
        <Box
          sx={{
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Tabs
            value={tabIndex}
            onChange={(_, v) => setTabIndex(v)}
            sx={{
              minHeight: 48,
              '& .MuiTab-root': {
                minHeight: 48,
                fontSize: '0.85rem',
                fontWeight: 600,
                textTransform: 'none',
                px: 3
              }
            }}
          >
            <Tab label="Reference" icon={<Users size={16} />} iconPosition="start" />
            <Tab label="Pipeline" icon={<Workflow size={16} />} iconPosition="start" />
            <Tab label="Documentation" icon={<Info size={16} />} iconPosition="start" />
          </Tabs>
        </Box>

        {/* Content Area */}
        <Box sx={{ flex: 1, overflowY: 'auto' }}>
          {tabIndex === 0 ? (
            // Reference View
            <ReferencePanel
              onCopy={handleCopyFeedback}
              onPromptSelect={onPromptSelect}
              selectedPatient={selectedPatient}
              onPatientSelect={onPatientSelect}
            />
          ) : tabIndex === 1 ? (
            // Pipeline View
            <Box sx={{ p: 2 }}>
              {/* Header Info (moved from top) */}
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  {isProcessing ? 'Processing query...' : lastQuery ? 'Last execution' : 'Ready for input'}
                </Typography>

                {hasActivity && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.disabled' }}>
                    <Info size={12} />
                    <Typography variant="caption" sx={{ fontSize: '0.65rem' }}>
                      Click steps for details
                    </Typography>
                  </Box>
                )}
              </Box>

              {isProcessing && !hasCompletedSteps ? (
                <Stack spacing={2}>
                  {[1, 2, 3, 4, 5].map(i => (
                    <Box key={i} sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
                      <Skeleton variant="rounded" width={32} height={32} sx={{ borderRadius: '8px', flexShrink: 0 }} />
                      <Box sx={{ flex: 1 }}>
                        <Skeleton variant="text" width="60%" />
                        <Skeleton variant="text" width="40%" />
                      </Box>
                    </Box>
                  ))}
                </Stack>
              ) : (
                <Stack spacing={0}>
                  {pipeline.map((step, index) => (
                    <PipelineStep
                      key={step.id}
                      step={step}
                      isLast={index === pipeline.length - 1}
                      queryText={lastQuery}
                      details={step.details}
                    />
                  ))}
                </Stack>
              )}

              {/* Tool calls */}
              <AnimatePresence>
                {toolCalls.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <Divider sx={{ my: 2 }} />
                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Wrench size={14} />
                        <Typography variant="caption" sx={{ fontWeight: 600 }}>
                          Tools Called
                        </Typography>
                      </Box>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                        {toolCalls.map((tool, idx) => (
                          <Chip
                            key={idx}
                            label={tool}
                            size="small"
                            variant="outlined"
                            sx={{
                              height: 22,
                              fontSize: '0.7rem',
                              borderColor: (theme) => alpha(theme.palette.primary.main, 0.3),
                              color: 'primary.main',
                            }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Sources */}
              <AnimatePresence>
                {sources.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <Divider sx={{ my: 2 }} />
                    <Box>
                      <Typography variant="caption" sx={{ fontWeight: 600, mb: 1, display: 'block' }}>
                        Retrieved Sources ({sources.length})
                      </Typography>
                      <Stack spacing={1}>
                        {sources.slice(0, 5).map((source, idx) => (
                          <SourceCard key={idx} source={source} index={idx} />
                        ))}
                        {sources.length > 5 && (
                          <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
                            +{sources.length - 5} more sources
                          </Typography>
                        )}
                      </Stack>
                    </Box>
                  </motion.div>
                )}
              </AnimatePresence>
            </Box>
          ) : (
            // Documentation View
            <DocumentationPanel />
          )}
        </Box>
      </Box>
    </div>
  );
}
