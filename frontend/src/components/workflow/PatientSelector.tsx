'use client';

import { useState, useMemo } from 'react';
import { Box, Typography, Card, CardContent, Chip, IconButton, Button, Stack, Tooltip, CardActionArea, Divider, CircularProgress, TextField, InputAdornment } from '@mui/material';
import { User, FileText, Database, RefreshCw, Search } from 'lucide-react';
import { alpha } from '@mui/material/styles';
import { PatientSummary } from '../../services/agentApi';

// Patient type for selection
interface SelectedPatient {
  id: string;
  name: string;
}

interface PatientInfo {
  id: string;
  name: string;
  age?: number;
  conditions: string[];
  description: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data?: any;
  chunk_count: number;
  resource_types: string[];
  isLive: boolean;
  isFeatured: boolean;
}

interface PatientSelectorProps {
  selectedPatient: SelectedPatient | null | undefined;
  onPatientSelect?: (patient: SelectedPatient | null) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onViewData?: (data: any) => void;
  featuredPatients: PatientInfo[];
  databasePatients: PatientInfo[];
  livePatients: PatientSummary[];
  isLoadingPatients: boolean;
  patientsError: string | null;
  onRefresh: () => void;
}

export function PatientSelector({
  selectedPatient,
  onPatientSelect,
  onViewData,
  featuredPatients,
  databasePatients,
  livePatients,
  isLoadingPatients,
  patientsError,
  onRefresh,
}: PatientSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('');

  // Filter database patients by search query
  const filteredDatabasePatients = useMemo(() => {
    if (!searchQuery.trim()) return databasePatients.slice(0, 50); // Show top 50 by default
    const q = searchQuery.toLowerCase();
    return databasePatients.filter(p => p.name.toLowerCase().includes(q)).slice(0, 100);
  }, [databasePatients, searchQuery]);

  // Find selected patient data
  const allPatients = [...featuredPatients, ...databasePatients];
  const selectedPatientData = selectedPatient
    ? allPatients.find(p => p.id === selectedPatient.id) || {
        id: selectedPatient.id,
        name: selectedPatient.name,
        age: undefined,
        conditions: [],
        description: 'Loading...',
        data: undefined,
        chunk_count: 0,
        resource_types: [],
        isLive: false,
        isFeatured: false,
      }
    : null;

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.secondary', fontWeight: 600 }}>
          <User size={16} />
          {selectedPatient ? 'Selected Patient' : 'Step 1: Select a Patient'}
          {livePatients.length > 0 && (
            <Chip
              label={`${livePatients.length} in DB`}
              size="small"
              icon={<Database size={12} />}
              sx={{ height: 18, fontSize: '0.6rem', ml: 0.5 }}
              color="success"
            />
          )}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {!selectedPatient && (
            <Tooltip title="Refresh patient list">
              <IconButton
                size="small"
                onClick={onRefresh}
                disabled={isLoadingPatients}
                sx={{ p: 0.5 }}
              >
                {isLoadingPatients ? (
                  <CircularProgress size={14} />
                ) : (
                  <RefreshCw size={14} />
                )}
              </IconButton>
            </Tooltip>
          )}
          {selectedPatient && onPatientSelect && (
            <Button
              size="small"
              variant="text"
              onClick={() => onPatientSelect(null)}
              sx={{ fontSize: '0.7rem', minWidth: 'auto', p: 0.5 }}
            >
              Change
            </Button>
          )}
        </Box>
      </Box>

      {/* Collapsed view when patient is selected */}
      {selectedPatient && selectedPatientData ? (
        <Card
          variant="outlined"
          sx={{
            bgcolor: (theme) => alpha(theme.palette.primary.main, 0.1),
            borderColor: 'primary.main',
            borderWidth: 2,
          }}
        >
          <CardContent sx={{ py: 1.5, px: 2, '&:last-child': { pb: 1.5 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: '50%',
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 600,
                }}
              >
                {selectedPatient.name.charAt(0)}
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2" fontWeight="bold">
                  {selectedPatient.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {selectedPatientData.age ? `${selectedPatientData.age} yrs` : ''}
                  {selectedPatientData.age && selectedPatientData.conditions?.[0] ? ' • ' : ''}
                  {selectedPatientData.conditions?.[0] || selectedPatientData.description}
                </Typography>
              </Box>
              {selectedPatientData.data && onViewData && (
                <Tooltip title="View patient data">
                  <IconButton
                    size="small"
                    onClick={() => onViewData(selectedPatientData.data)}
                  >
                    <FileText size={16} />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </CardContent>
        </Card>
      ) : (
        /* Full patient list when none selected */
        <Box>
          {/* Loading state */}
          {isLoadingPatients && featuredPatients.length === 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 4 }}>
              <CircularProgress size={24} />
              <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                Loading patients...
              </Typography>
            </Box>
          )}
          {/* Error state */}
          {patientsError && (
            <Typography variant="caption" color="error" sx={{ textAlign: 'center', py: 2 }}>
              {patientsError}
            </Typography>
          )}

          {/* Featured Patients Section */}
          <Typography variant="caption" sx={{ fontWeight: 600, mb: 1, display: 'block', color: 'text.secondary' }}>
            Featured Patients (with full FHIR data)
          </Typography>
          <Stack spacing={1.5} sx={{ mb: 2 }}>
            {featuredPatients.map((p) => {
              const isSelected = selectedPatient?.id === p.id;
              return (
                <Card
                  key={p.id}
                  variant="outlined"
                  sx={{
                    bgcolor: (theme) => isSelected
                      ? alpha(theme.palette.primary.main, 0.15)
                      : alpha(theme.palette.background.paper, 0.4),
                    backdropFilter: 'blur(10px)',
                    borderColor: isSelected ? 'primary.main' : 'divider',
                    borderWidth: isSelected ? 2 : 1,
                    transition: 'all 0.2s',
                    '&:hover': {
                      bgcolor: (theme) => isSelected
                        ? alpha(theme.palette.primary.main, 0.2)
                        : alpha(theme.palette.background.paper, 0.6),
                      borderColor: 'primary.main',
                    },
                    cursor: 'pointer',
                    position: 'relative',
                  }}
                >
                  <Box
                    onClick={() => {
                      if (onPatientSelect) {
                        onPatientSelect(isSelected ? null : { id: p.id, name: p.name });
                      } else if (p.data && onViewData) {
                        onViewData(p.data);
                      }
                    }}
                    sx={{ p: 1.5, display: 'flex', alignItems: 'center', gap: 1.5 }}
                  >
                    <Box
                      sx={{
                        width: 32,
                        height: 32,
                        borderRadius: '50%',
                        bgcolor: isSelected ? 'primary.main' : 'action.selected',
                        color: isSelected ? 'primary.contrastText' : 'text.primary',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 600,
                        fontSize: '0.8rem',
                        flexShrink: 0,
                      }}
                    >
                      {p.name.charAt(0)}
                    </Box>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Typography variant="subtitle2" fontWeight="bold" noWrap>
                          {p.name}
                        </Typography>
                        {isSelected && (
                          <Chip label="Selected" size="small" color="primary" sx={{ height: 16, fontSize: '0.55rem' }} />
                        )}
                      </Box>
                      <Typography variant="caption" color="text.secondary" noWrap>
                        {p.age} yrs • {p.conditions[0]}
                      </Typography>
                    </Box>
                    {p.data && onViewData && (
                      <Tooltip title="View FHIR data">
                        <IconButton
                          size="small"
                          onClick={(e) => { e.stopPropagation(); onViewData(p.data); }}
                          sx={{ flexShrink: 0 }}
                        >
                          <FileText size={14} />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </Card>
              );
            })}
          </Stack>

          {/* Database Patients Section */}
          {databasePatients.length > 0 && (
            <>
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                  Patient Directory ({databasePatients.length.toLocaleString()} patients)
                </Typography>
              </Box>
              <TextField
                size="small"
                placeholder="Search patients by name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                fullWidth
                sx={{ mb: 1, '& .MuiInputBase-input': { fontSize: '0.8rem', py: 0.75 } }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search size={14} />
                    </InputAdornment>
                  ),
                }}
              />
              {!searchQuery && (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem', mb: 0.5, display: 'block' }}>
                  Showing top 50 by data richness. Type to search all {databasePatients.length.toLocaleString()}.
                </Typography>
              )}
              {searchQuery && (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem', mb: 0.5, display: 'block' }}>
                  {filteredDatabasePatients.length} results{filteredDatabasePatients.length === 100 ? ' (showing first 100)' : ''}
                </Typography>
              )}
              <Box sx={{ maxHeight: 300, overflowY: 'auto', pr: 0.5 }}>
                <Stack spacing={1}>
                  {filteredDatabasePatients.map((p) => {
                    const isSelected = selectedPatient?.id === p.id;
                    return (
                      <Card
                        key={p.id}
                        variant="outlined"
                        sx={{
                          bgcolor: (theme) => isSelected
                            ? alpha(theme.palette.primary.main, 0.15)
                            : alpha(theme.palette.background.paper, 0.3),
                          borderColor: isSelected ? 'primary.main' : 'divider',
                          borderWidth: isSelected ? 2 : 1,
                          cursor: 'pointer',
                          '&:hover': { borderColor: 'primary.main' },
                        }}
                      >
                        <CardActionArea
                          onClick={() => {
                            if (onPatientSelect) {
                              onPatientSelect(isSelected ? null : { id: p.id, name: p.name });
                            }
                          }}
                          sx={{ p: 1 }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Box
                              sx={{
                                width: 28,
                                height: 28,
                                borderRadius: '50%',
                                bgcolor: isSelected ? 'primary.main' : 'action.hover',
                                color: isSelected ? 'primary.contrastText' : 'text.secondary',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontWeight: 600,
                                fontSize: '0.7rem',
                                flexShrink: 0,
                              }}
                            >
                              {p.name.charAt(0)}
                            </Box>
                            <Box sx={{ flex: 1, minWidth: 0 }}>
                              <Typography variant="caption" fontWeight="bold" noWrap sx={{ display: 'block' }}>
                                {p.name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                                {p.chunk_count} chunks • {p.resource_types.slice(0, 2).join(', ')}
                                {p.resource_types.length > 2 && '...'}
                              </Typography>
                            </Box>
                            {isSelected && (
                              <Chip label="✓" size="small" color="primary" sx={{ height: 16, minWidth: 16, fontSize: '0.6rem', p: 0 }} />
                            )}
                          </Box>
                        </CardActionArea>
                      </Card>
                    );
                  })}
                </Stack>
              </Box>
            </>
          )}
        </Box>
      )}
    </Box>
  );
}
