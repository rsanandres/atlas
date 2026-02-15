import { useState, useEffect, useRef } from 'react';
import { Box, Divider } from '@mui/material';

// Import sub-components
import { PatientSelector } from './PatientSelector';
import { PatientDataModal } from './PatientDataModal';
import { RecommendedPrompts } from './RecommendedPrompts';

// Shared patient metadata + prompts
import { FEATURED_PATIENTS, RECOMMENDED_PROMPTS } from '../../data/featured-patients';

// FHIR bundles (shared module)
import { FHIR_BUNDLES } from '../../data/fhir-bundles';

import { PatientSummary } from '../../services/agentApi';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FhirBundle = any;

// Static patient data from pre-generated JSON (served from /public/data/patients.json)
interface StaticPatient {
  name: string;
  patient_id: string;
  chunks: number;
}

// Build PERSONAS from shared data, attaching FHIR bundles where available
const PERSONAS = FEATURED_PATIENTS.map(p => ({
  id: p.id,
  name: p.name,
  age: p.age,
  conditions: p.conditions,
  description: p.description,
  data: FHIR_BUNDLES[p.id] as FhirBundle | undefined,
}));

// Patient type for selection
interface SelectedPatient {
  id: string;
  name: string;
}

interface ReferencePanelProps {
  onCopy: (text: string) => void;
  onPromptSelect?: (text: string) => void;
  selectedPatient?: SelectedPatient | null;
  onPatientSelect?: (patient: SelectedPatient | null) => void;
}

export function ReferencePanel({ onCopy, onPromptSelect, selectedPatient, onPatientSelect }: ReferencePanelProps) {
  const promptsRef = useRef<HTMLDivElement>(null);

  // Modal state
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [selectedJson, setSelectedJson] = useState<any>(null);

  // Live patient data from API
  const [livePatients, setLivePatients] = useState<PatientSummary[]>([]);
  const [isLoadingPatients, setIsLoadingPatients] = useState(false);
  const [patientsError, setPatientsError] = useState<string | null>(null);

  const fetchPatients = async () => {
    setIsLoadingPatients(true);
    setPatientsError(null);
    try {
      // Load from static JSON (served from /public/data/patients.json by Vercel CDN)
      // This avoids the slow /db/patients RDS query that times out on 132K rows
      const response = await fetch('/data/patients.json');
      if (!response.ok) throw new Error(`Failed to load patients: ${response.status}`);
      const data: StaticPatient[] = await response.json();
      const patients: PatientSummary[] = data.map(p => ({
        id: p.patient_id,
        name: p.name,
        chunk_count: p.chunks,
        resource_types: [],
      }));
      setLivePatients(patients);
    } catch (err) {
      console.error('Failed to fetch patients:', err);
      setPatientsError('Failed to load patient directory');
    } finally {
      setIsLoadingPatients(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, []);

  // Auto-scroll to prompts when patient is selected
  useEffect(() => {
    if (selectedPatient && promptsRef.current) {
      setTimeout(() => {
        promptsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [selectedPatient]);

  // Featured patients (those with full local FHIR data)
  const featuredPatients = PERSONAS.map(p => {
    const liveData = livePatients.find(lp => lp.id === p.id);
    return {
      ...p,
      isLive: !!liveData,
      isFeatured: true,
      chunk_count: liveData?.chunk_count || 0,
      resource_types: liveData?.resource_types || [] as string[],
    };
  });

  // Database patients (excluding featured ones)
  const featuredIds = new Set(PERSONAS.map(p => p.id));
  const databasePatients = livePatients
    .filter(lp => !featuredIds.has(lp.id))
    .map(liveP => ({
      id: liveP.id,
      name: liveP.name,
      age: undefined as number | undefined,
      conditions: [] as string[],
      description: `${liveP.chunk_count} records • ${liveP.resource_types.length} resource types`,
      data: undefined,
      chunk_count: liveP.chunk_count,
      resource_types: liveP.resource_types,
      isLive: true,
      isFeatured: false,
    }));

  const allPatients = [...featuredPatients, ...databasePatients];

  const handlePromptClick = (prompt: string) => {
    if (onPromptSelect) {
      onPromptSelect(prompt);
    } else {
      navigator.clipboard.writeText(prompt);
      onCopy('Copied Prompt');
    }
  };

  // Find the name for the modal
  const modalPatientName = selectedJson
    ? allPatients.find(p => p.data === selectedJson)?.name || 'Unknown Patient'
    : undefined;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, p: 2, pb: 4 }}>
      {/* Step 1: Patient Selection */}
      <PatientSelector
        selectedPatient={selectedPatient}
        onPatientSelect={onPatientSelect}
        onViewData={setSelectedJson}
        featuredPatients={featuredPatients}
        databasePatients={databasePatients}
        livePatients={livePatients}
        isLoadingPatients={isLoadingPatients}
        patientsError={patientsError}
        onRefresh={fetchPatients}
      />

      {/* Step 2: Recommended Prompts (only shown after patient selection) */}
      {selectedPatient && (
        <div ref={promptsRef}>
          <Divider sx={{ mb: 3 }} />
          <RecommendedPrompts
            prompts={RECOMMENDED_PROMPTS}
            onPromptClick={handlePromptClick}
          />
        </div>
      )}

      {/* Patient Details Modal */}
      <PatientDataModal
        open={!!selectedJson}
        onClose={() => setSelectedJson(null)}
        data={selectedJson}
        patientName={modalPatientName}
      />
    </Box>
  );
}
