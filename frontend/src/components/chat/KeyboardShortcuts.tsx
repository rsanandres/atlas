'use client';

import { Box, Dialog, DialogTitle, DialogContent, Typography, IconButton, alpha } from '@mui/material';
import { X } from 'lucide-react';

interface KeyboardShortcutsProps {
  open: boolean;
  onClose: () => void;
}

const shortcuts = [
  { keys: ['Enter'], description: 'Send message' },
  { keys: ['Shift', 'Enter'], description: 'New line' },
  { keys: ['Cmd', '/'], description: 'Show keyboard shortcuts' },
];

function Kbd({ children }: { children: string }) {
  return (
    <Box
      component="kbd"
      sx={{
        display: 'inline-block',
        px: 1,
        py: 0.25,
        mx: 0.25,
        borderRadius: '4px',
        bgcolor: (theme) => alpha(theme.palette.common.white, 0.08),
        border: '1px solid',
        borderColor: 'divider',
        fontSize: '0.75rem',
        fontFamily: 'var(--font-geist-mono)',
        lineHeight: 1.6,
        minWidth: 24,
        textAlign: 'center',
      }}
    >
      {children}
    </Box>
  );
}

export function KeyboardShortcuts({ open, onClose }: KeyboardShortcutsProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        Keyboard Shortcuts
        <IconButton size="small" onClick={onClose}>
          <X size={18} />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, py: 1 }}>
          {shortcuts.map((shortcut, i) => (
            <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {shortcut.description}
              </Typography>
              <Box>
                {shortcut.keys.map((key, j) => (
                  <span key={j}>
                    <Kbd>{key}</Kbd>
                    {j < shortcut.keys.length - 1 && (
                      <Typography variant="caption" color="text.disabled" sx={{ mx: 0.25 }}>+</Typography>
                    )}
                  </span>
                ))}
              </Box>
            </Box>
          ))}
        </Box>
      </DialogContent>
    </Dialog>
  );
}
