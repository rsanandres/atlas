'use client';

import React from 'react';
import { Box, Typography, Button, alpha } from '@mui/material';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            p: 4,
            textAlign: 'center',
            bgcolor: 'background.default',
          }}
        >
          <Box
            sx={{
              p: 4,
              borderRadius: '16px',
              bgcolor: (theme) => alpha(theme.palette.background.paper, 0.6),
              border: '1px solid',
              borderColor: 'divider',
              maxWidth: 400,
            }}
          >
            <AlertCircle size={48} style={{ marginBottom: 16, opacity: 0.6 }} />
            <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
              Something went wrong
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              {this.state.error?.message || 'An unexpected error occurred. Please try again.'}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<RefreshCw size={16} />}
              onClick={() => this.setState({ hasError: false, error: undefined })}
            >
              Try Again
            </Button>
          </Box>
        </Box>
      );
    }

    return this.props.children;
  }
}
