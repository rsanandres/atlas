'use client';

import { useState, useEffect } from 'react';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  IconButton,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  alpha,
} from '@mui/material';
import { Plus, Trash2, Edit, X } from 'lucide-react';
import { useSessions } from '@/hooks/useSessions';
import { SessionMetadata } from '@/types';

interface SessionSidebarProps {
  open: boolean;
  onClose: () => void;
  onSessionSelect: (sessionId: string) => void;
}

export function SessionSidebar({ open, onClose, onSessionSelect }: SessionSidebarProps) {
  const {
    sessions,
    activeSessionId,
    isLoading,
    createNewSession,
    switchSession,
    removeSession,
    updateSession,
    checkSessionLimit,
    maxSessions,
  } = useSessions();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<SessionMetadata | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [sessionToEdit, setSessionToEdit] = useState<SessionMetadata | null>(null);
  const [editName, setEditName] = useState('');
  const [limitDialogOpen, setLimitDialogOpen] = useState(false);

  const handleNewSession = async () => {
    try {
      const atLimit = await checkSessionLimit();
      if (atLimit) {
        setLimitDialogOpen(true);
        return;
      }

      const newSession = await createNewSession();
      if (newSession) {
        switchSession(newSession.session_id);
        onSessionSelect(newSession.session_id);
      }
    } catch (err) {
      if (err instanceof Error && err.message === 'SESSION_LIMIT_EXCEEDED') {
        setLimitDialogOpen(true);
      }
    }
  };

  const handleSessionClick = (sessionId: string) => {
    switchSession(sessionId);
    onSessionSelect(sessionId);
  };

  const handleDeleteClick = (session: SessionMetadata, e: React.MouseEvent) => {
    e.stopPropagation();
    setSessionToDelete(session);
    setDeleteDialogOpen(true);
  };

  const handleEditClick = (session: SessionMetadata, e: React.MouseEvent) => {
    e.stopPropagation();
    setSessionToEdit(session);
    setEditName(session.name || '');
    setEditDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (sessionToDelete) {
      await removeSession(sessionToDelete.session_id);
      setDeleteDialogOpen(false);
      setSessionToDelete(null);
    }
  };

  const confirmEdit = async () => {
    if (sessionToEdit) {
      await updateSession(sessionToEdit.session_id, { name: editName });
      setEditDialogOpen(false);
      setSessionToEdit(null);
      setEditName('');
    }
  };

  const formatDate = (dateString: string) => {
    // Use a consistent format that works on both server and client
    // Avoid using Date.now() or new Date() during render to prevent hydration mismatches
    if (typeof window === 'undefined') {
      // Server-side: return a safe placeholder
      return dateString;
    }
    
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      // Use a consistent date format
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
    } catch {
      return dateString;
    }
  };

  return (
    <>
      <Drawer
        anchor="left"
        open={open}
        onClose={onClose}
        sx={{
          '& .MuiDrawer-paper': {
            width: 280,
            bgcolor: 'background.paper',
            borderRight: 1,
            borderColor: 'divider',
          },
        }}
      >
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Sessions
            </Typography>
            <IconButton size="small" onClick={onClose}>
              <X size={18} />
            </IconButton>
          </Box>
          <Button
            fullWidth
            variant="contained"
            startIcon={<Plus size={18} />}
            onClick={handleNewSession}
            disabled={isLoading || sessions.length >= maxSessions}
            sx={{ mb: 1 }}
          >
            New Session
          </Button>
          {sessions.length >= maxSessions && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center' }}>
              Maximum {maxSessions} sessions
            </Typography>
          )}
        </Box>

        <List sx={{ flex: 1, overflow: 'auto', p: 0 }}>
          {isLoading && sessions.length === 0 ? (
            <ListItem>
              <ListItemText primary="Loading sessions..." />
            </ListItem>
          ) : sessions.length === 0 ? (
            <ListItem>
              <ListItemText
                primary="No sessions"
                secondary="Create a new session to get started"
              />
            </ListItem>
          ) : (
            sessions.map((session) => {
              const isActive = session.session_id === activeSessionId;
              return (
                <ListItem
                  key={session.session_id}
                  disablePadding
                  sx={{
                    '&:hover .session-actions': { opacity: 1 },
                  }}
                >
                  <ListItemButton
                    selected={isActive}
                    onClick={() => handleSessionClick(session.session_id)}
                    sx={{
                      flexDirection: 'column',
                      alignItems: 'flex-start',
                      py: 1.5,
                      px: 2,
                      bgcolor: isActive ? (theme) => alpha(theme.palette.primary.main, 0.1) : 'transparent',
                      '&:hover': {
                        bgcolor: (theme) => alpha(theme.palette.primary.main, 0.05),
                      },
                    }}
                  >
                    <Box sx={{ width: '100%', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography
                          variant="subtitle2"
                          sx={{
                            fontWeight: isActive ? 600 : 500,
                            mb: 0.5,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {session.name || 'New Chat'}
                        </Typography>
                        {session.first_message_preview && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{
                              display: 'block',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              mb: 0.5,
                            }}
                          >
                            {session.first_message_preview}
                          </Typography>
                        )}
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(session.last_activity)} • {session.message_count} messages
                        </Typography>
                      </Box>
                      <Box
                        className="session-actions"
                        sx={{
                          opacity: 0,
                          transition: 'opacity 0.2s',
                          display: 'flex',
                          gap: 0.5,
                          ml: 1,
                        }}
                      >
                        <IconButton
                          size="small"
                          onClick={(e) => handleEditClick(session, e)}
                          sx={{ p: 0.5 }}
                        >
                          <Edit size={16} />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={(e) => handleDeleteClick(session, e)}
                          sx={{ p: 0.5 }}
                        >
                          <Trash2 size={16} />
                        </IconButton>
                      </Box>
                    </Box>
                  </ListItemButton>
                </ListItem>
              );
            })
          )}
        </List>
      </Drawer>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Session?</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{sessionToDelete?.name || 'this session'}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={confirmDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Session Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)}>
        <DialogTitle>Edit Session</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Session Name"
            fullWidth
            variant="outlined"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={confirmEdit} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Session Limit Dialog */}
      <Dialog open={limitDialogOpen} onClose={() => setLimitDialogOpen(false)}>
        <DialogTitle>Session Limit Reached</DialogTitle>
        <DialogContent>
          <Typography>
            You have reached the maximum of {maxSessions} sessions. Please delete an existing session to create a new one.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLimitDialogOpen(true)} variant="contained">
            OK
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
