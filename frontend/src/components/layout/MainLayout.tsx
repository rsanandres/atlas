'use client';

import { useState, useEffect } from 'react';
import { Box, Drawer, Fab, alpha, useMediaQuery, useTheme } from '@mui/material';
// motion removed — React 19 strict mode breaks framer-motion initial animations
import { PanelRight, X } from 'lucide-react';

interface MainLayoutProps {
  chatPanel: React.ReactNode;
  workflowPanel: React.ReactNode;
  observabilityPanel: React.ReactNode;
  closeRightPanel?: boolean;
}

export function MainLayout({ chatPanel, workflowPanel, observabilityPanel, closeRightPanel }: MainLayoutProps) {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg')); // >1200px
  // Start closed on mobile/tablet so the modal backdrop doesn't block the page
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  // Close drawer when prompt is sent (mobile)
  useEffect(() => {
    if (closeRightPanel && !isDesktop) {
      setRightPanelOpen(false);
    }
  }, [closeRightPanel, isDesktop]);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: 'background.default',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background gradient effects */}
      <Box
        sx={{
          position: 'fixed',
          top: '-20%',
          left: '-10%',
          width: '50%',
          height: '50%',
          borderRadius: '50%',
          background: (theme) => `radial-gradient(circle, ${alpha(theme.palette.primary.main, 0.08)} 0%, transparent 60%)`,
          pointerEvents: 'none',
          filter: 'blur(60px)',
        }}
      />
      <Box
        sx={{
          position: 'fixed',
          bottom: '-20%',
          right: '-10%',
          width: '60%',
          height: '60%',
          borderRadius: '50%',
          background: (theme) => `radial-gradient(circle, ${alpha(theme.palette.secondary.main, 0.06)} 0%, transparent 60%)`,
          pointerEvents: 'none',
          filter: 'blur(80px)',
        }}
      />

      {/* Main content */}
      <Box
        sx={{
          position: 'relative',
          zIndex: 1,
          height: '100vh',
          p: 2,
          display: 'flex',
          gap: 2,
        }}
      >
        {/* Left side - Chat (Flex fill) */}
        <div
          data-tour="chat"
          style={{ flex: 1, height: '100%', minWidth: 0 }}
        >
          {chatPanel}
        </div>

        {/* Right side - Desktop: inline panels; Mobile/Tablet: drawer */}
        {isDesktop ? (
          <Box
            sx={{
              flex: '0 0 32%',
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              height: '100%',
            }}
          >
            <Box data-tour="workflow" sx={{ flex: '1 1 50%', minHeight: 0 }}>
              {workflowPanel}
            </Box>
            <Box data-tour="observability" sx={{ flex: '1 1 50%', minHeight: 0 }}>
              {observabilityPanel}
            </Box>
          </Box>
        ) : (
          <>
            <Drawer
              anchor="right"
              open={rightPanelOpen}
              onClose={() => setRightPanelOpen(false)}
              PaperProps={{
                sx: {
                  width: '85vw',
                  maxWidth: 480,
                  bgcolor: 'background.default',
                  p: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 2,
                },
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Fab size="small" onClick={() => setRightPanelOpen(false)} sx={{ boxShadow: 'none', bgcolor: 'action.hover' }}>
                  <X size={18} />
                </Fab>
              </Box>
              <Box sx={{ flex: '1 1 50%', minHeight: 0, overflow: 'auto' }}>
                {workflowPanel}
              </Box>
              <Box sx={{ flex: '1 1 50%', minHeight: 0, overflow: 'auto' }}>
                {observabilityPanel}
              </Box>
            </Drawer>

            <Box
              onClick={() => setRightPanelOpen(true)}
              sx={{
                position: 'fixed',
                right: 0,
                top: '50%',
                transform: 'translateY(-50%)',
                zIndex: 10,
                width: 28,
                height: 52,
                borderRadius: '8px 0 0 8px',
                bgcolor: (theme) => alpha(theme.palette.primary.main, 0.7),
                color: 'primary.contrastText',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                '&:hover': { bgcolor: 'primary.main' },
                transition: 'background-color 0.2s',
              }}
            >
              <PanelRight size={16} />
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
}
