'use client';

import { useState, useEffect } from 'react';
import { Box, Typography, Button, IconButton, alpha, useTheme } from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronRight, ChevronLeft, MessageSquare, Workflow, Activity, BookOpen, Users, Bug } from 'lucide-react';

const STORAGE_KEY = 'hcai-tour-completed';

interface TourStep {
  title: string;
  description: string;
  icon: React.ElementType;
  position: 'left' | 'right';
  highlight: string; // CSS selector hint (for user context, not programmatic)
}

const TOUR_STEPS: TourStep[] = [
  {
    title: 'Chat Panel',
    description: 'Ask medical questions in natural language. The AI agent will search clinical records and reason through the data to answer.',
    icon: MessageSquare,
    position: 'left',
    highlight: 'chat',
  },
  {
    title: 'Reference Panel',
    description: 'Browse featured patients, switch between patients, and pick from recommended questions.',
    icon: Users,
    position: 'right',
    highlight: 'reference',
  },
  {
    title: 'Pipeline View',
    description: 'Watch your query flow through the RAG pipeline in real time: PII masking, vector search, LLM reasoning, and response synthesis.',
    icon: Workflow,
    position: 'right',
    highlight: 'pipeline',
  },
  {
    title: 'Observability Panel',
    description: 'Monitor system health, CloudWatch metrics, and service status. You\'re in debug mode by default to see the agent\'s internals.',
    icon: Activity,
    position: 'right',
    highlight: 'observability',
  },
  {
    title: 'Debug Mode',
    description: 'Debug mode is on by default so you can see every step the agent takes. Toggle it off anytime with the bug icon in the chat header.',
    icon: Bug,
    position: 'left',
    highlight: 'debug',
  },
];

interface OnboardingTourProps {
  /** If true, force-show the tour even if previously completed */
  forceShow?: boolean;
}

export function OnboardingTour({ forceShow }: OnboardingTourProps) {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);
  const theme = useTheme();

  useEffect(() => {
    if (forceShow) {
      setVisible(true);
      return;
    }
    const completed = localStorage.getItem(STORAGE_KEY);
    if (!completed) {
      // Small delay so the main UI renders first
      const timer = setTimeout(() => setVisible(true), 600);
      return () => clearTimeout(timer);
    }
  }, [forceShow]);

  const dismiss = () => {
    setVisible(false);
    localStorage.setItem(STORAGE_KEY, 'true');
  };

  const next = () => {
    if (step < TOUR_STEPS.length - 1) {
      setStep(step + 1);
    } else {
      dismiss();
    }
  };

  const prev = () => {
    if (step > 0) setStep(step - 1);
  };

  if (!visible) return null;

  const current = TOUR_STEPS[step];
  const Icon = current.icon;
  const isLast = step === TOUR_STEPS.length - 1;

  return (
    <AnimatePresence>
      {visible && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 9998,
              backgroundColor: 'rgba(0,0,0,0.5)',
              backdropFilter: 'blur(2px)',
            }}
            onClick={dismiss}
          />

          {/* Tour card */}
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.25 }}
            style={{
              position: 'fixed',
              bottom: 24,
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 9999,
              width: '90%',
              maxWidth: 460,
            }}
          >
            <Box
              sx={{
                bgcolor: alpha(theme.palette.background.paper, 0.95),
                backdropFilter: 'blur(20px)',
                borderRadius: '16px',
                border: '1px solid',
                borderColor: alpha(theme.palette.primary.main, 0.2),
                p: 3,
                boxShadow: `0 20px 60px ${alpha(theme.palette.common.black, 0.4)}`,
              }}
            >
              {/* Close button */}
              <IconButton
                onClick={dismiss}
                size="small"
                sx={{ position: 'absolute', top: 8, right: 8, color: 'text.disabled' }}
              >
                <X size={16} />
              </IconButton>

              {/* Step indicator */}
              <Box sx={{ display: 'flex', gap: 0.5, mb: 2 }}>
                {TOUR_STEPS.map((_, i) => (
                  <Box
                    key={i}
                    sx={{
                      height: 3,
                      flex: 1,
                      borderRadius: 2,
                      bgcolor: i <= step
                        ? 'primary.main'
                        : alpha(theme.palette.text.disabled, 0.2),
                      transition: 'background-color 0.3s',
                    }}
                  />
                ))}
              </Box>

              {/* Content */}
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: '10px',
                    bgcolor: alpha(theme.palette.primary.main, 0.15),
                    color: 'primary.main',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Icon size={20} />
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 0.5 }}>
                    {current.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.5 }}>
                    {current.description}
                  </Typography>
                </Box>
              </Box>

              {/* Navigation */}
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 2.5 }}>
                <Typography variant="caption" color="text.disabled">
                  {step + 1} of {TOUR_STEPS.length}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  {step > 0 && (
                    <Button
                      size="small"
                      onClick={prev}
                      startIcon={<ChevronLeft size={14} />}
                      sx={{ textTransform: 'none', color: 'text.secondary' }}
                    >
                      Back
                    </Button>
                  )}
                  <Button
                    size="small"
                    variant="contained"
                    onClick={next}
                    endIcon={!isLast ? <ChevronRight size={14} /> : undefined}
                    sx={{ textTransform: 'none', minWidth: 80 }}
                  >
                    {isLast ? 'Got it!' : 'Next'}
                  </Button>
                </Box>
              </Box>
            </Box>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
