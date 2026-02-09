'use client';

import { useState } from 'react';
import { Box, Typography, Chip, Collapse, alpha } from '@mui/material';
import { motion } from 'framer-motion';
import { FileText, Calendar, User, ChevronDown, ChevronRight } from 'lucide-react';
import { AgentDocument } from '@/types';

interface SourceCardProps {
  source: AgentDocument;
  index: number;
}

export function SourceCard({ source, index }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const metadata = source.metadata || {};

  // Safely extract metadata values as strings
  const resourceType = metadata.resourceType ? String(metadata.resourceType) : null;
  const effectiveDate = metadata.effectiveDate ? String(metadata.effectiveDate).split('T')[0] : null;
  const patientId = metadata.patientId ? String(metadata.patientId).slice(0, 8) : null;

  // Score display
  const score = source.score;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          p: 1.5,
          borderRadius: '8px',
          bgcolor: (theme) => alpha(theme.palette.common.white, 0.02),
          border: '1px solid',
          borderColor: expanded
            ? (theme) => alpha(theme.palette.primary.main, 0.3)
            : 'divider',
          '&:hover': {
            bgcolor: (theme) => alpha(theme.palette.common.white, 0.04),
            borderColor: (theme) => alpha(theme.palette.primary.main, 0.3),
          },
          transition: 'all 0.2s ease',
          cursor: 'pointer',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
          <Box
            sx={{
              p: 0.5,
              borderRadius: '6px',
              bgcolor: (theme) => alpha(theme.palette.primary.main, 0.1),
              color: 'primary.main',
            }}
          >
            <FileText size={14} />
          </Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              variant="caption"
              sx={{
                fontWeight: 500,
                display: 'block',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {source.doc_id}
            </Typography>
            {!expanded && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  fontSize: '0.7rem',
                  lineHeight: 1.4,
                }}
              >
                {source.content_preview}
              </Typography>
            )}
          </Box>
          <Box sx={{ color: 'text.disabled', flexShrink: 0, mt: 0.25 }}>
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </Box>
        </Box>

        {/* Score bar */}
        {typeof score === 'number' && (
          <Box sx={{ mt: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box sx={{ flex: 1, height: 4, borderRadius: 2, bgcolor: 'divider' }}>
                <Box
                  sx={{
                    width: `${Math.min(score * 100, 100)}%`,
                    height: '100%',
                    borderRadius: 2,
                    bgcolor: score > 0.7 ? 'success.main' : score > 0.4 ? 'warning.main' : 'error.main',
                    transition: 'width 0.3s ease',
                  }}
                />
              </Box>
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', minWidth: 30, textAlign: 'right' }}>
                {(score * 100).toFixed(0)}%
              </Typography>
            </Box>
          </Box>
        )}

        {/* Metadata chips */}
        {(resourceType || effectiveDate || patientId) && (
          <Box sx={{ display: 'flex', gap: 0.5, mt: 1, flexWrap: 'wrap' }}>
            {resourceType && (
              <Chip
                size="small"
                label={resourceType}
                sx={{ height: 18, fontSize: '0.65rem' }}
              />
            )}
            {effectiveDate && (
              <Chip
                size="small"
                icon={<Calendar size={10} />}
                label={effectiveDate}
                sx={{ height: 18, fontSize: '0.65rem', '& .MuiChip-icon': { ml: 0.5 } }}
              />
            )}
            {patientId && (
              <Chip
                size="small"
                icon={<User size={10} />}
                label={patientId}
                sx={{ height: 18, fontSize: '0.65rem', '& .MuiChip-icon': { ml: 0.5 } }}
              />
            )}
          </Box>
        )}

        {/* Expanded content */}
        <Collapse in={expanded}>
          <Box sx={{ mt: 1.5, pt: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                display: 'block',
                whiteSpace: 'pre-wrap',
                fontSize: '0.7rem',
                lineHeight: 1.5,
                mb: 1,
              }}
            >
              {source.content_preview}
            </Typography>

            {/* Full metadata */}
            {Object.keys(metadata).length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.65rem', color: 'text.disabled', display: 'block', mb: 0.5 }}>
                  Metadata
                </Typography>
                {Object.entries(metadata).map(([key, value]) => (
                  <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.25 }}>
                    <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.65rem' }}>
                      {key}
                    </Typography>
                    <Typography variant="caption" sx={{ fontSize: '0.65rem', maxWidth: '60%', textAlign: 'right', wordBreak: 'break-all' }}>
                      {String(value)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}
          </Box>
        </Collapse>
      </Box>
    </motion.div>
  );
}
