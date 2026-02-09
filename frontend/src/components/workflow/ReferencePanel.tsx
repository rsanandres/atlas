import { useState, useEffect } from 'react';
import { Box, Divider } from '@mui/material';

// Import sub-components
import { PatientSelector } from './PatientSelector';
import { PatientDataModal } from './PatientDataModal';
import { RecommendedPrompts } from './RecommendedPrompts';

// Import data
import larsonJson from '../../data/personas/larson.json';
import ziemeJson from '../../data/personas/zieme.json';
import christiansenJson from '../../data/personas/christiansen.json';
import hegmannJson from '../../data/personas/hegmann.json';
import herzogJson from '../../data/personas/herzog.json';
import adamJson from '../../data/personas/abbott_adam.json';
import alvaJson from '../../data/personas/abbott_alva.json';
import amayaJson from '../../data/personas/abbott_amaya.json';

import { listPatients, PatientSummary } from '../../services/agentApi';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FhirBundle = any;

// Local persona data with full FHIR bundles for detailed view
const LOCAL_PERSONA_DATA: Record<string, { name: string; age: number; conditions: string[]; description: string; data: FhirBundle }> = {
  "5e81d5b2-af01-4367-9b2e-0cdf479094a4": { name: "Danial Larson", age: 65, conditions: ["Recurrent rectal polyp", "Hypertension", "Chronic kidney disease"], description: "Older male with multiple chronic conditions.", data: larsonJson },
  "d8d9460b-4cb6-47f9-a94f-9e58390204b2": { name: "Ron Zieme", age: 86, conditions: ["Hypertension", "Fibromyalgia", "Osteoporosis", "Coronary Heart Disease"], description: "Elderly female with complex history including MI and heart disease.", data: ziemeJson },
  "0beb6802-3353-4144-8ae3-97176bce86c3": { name: "Doug Christiansen", age: 24, conditions: ["Chronic sinusitis"], description: "Young adult with chronic sinus issues.", data: christiansenJson },
  "6a4168a1-2cfd-4269-8139-8a4a663adfe7": { name: "Jamie Hegmann", age: 71, conditions: ["Coronary Heart Disease", "Myocardial Infarction History"], description: "Female patient with significant cardiac history.", data: hegmannJson },
  "7f7ad77a-5dd5-4df0-ba36-f4f1e4b6d368": { name: "Carlo Herzog", age: 23, conditions: ["Childhood asthma", "Allergic rhinitis", "Nut allergy"], description: "Young male with multiple allergies and asthma.", data: herzogJson },
  "53fcaff1-eb44-4257-819b-50b47f311edf": { name: "Adam Abbott", age: 31, conditions: ["Normal Pregnancy"], description: "Young female with active pregnancy.", data: adamJson },
  "f883318e-9a81-4f77-9cff-5318a00b777f": { name: "Alva Abbott", age: 67, conditions: ["Prediabetes"], description: "Older male managing prediabetes.", data: alvaJson },
  "4b7098a8-13b8-4916-a379-6ae2c8a70a8a": { name: "Amaya Abbott", age: 69, conditions: ["Hypertension", "Chronic sinusitis", "Concussion History"], description: "Older male with hypertension and history of head injury.", data: amayaJson },
};

const PERSONAS = Object.entries(LOCAL_PERSONA_DATA).map(([id, data]) => ({ id, ...data }));

const RECOMMENDED_PROMPTS = [
  "What are the patient's active conditions?",
  "Summarize the patient's medication history.",
  "Does the patient have any known allergies?",
  "What are the patient's recent lab results?",
  "Show me the timeline of clinical events.",
  "When was the patient's last encounter?",
];

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
      const patients = await listPatients();
      setLivePatients(patients);
    } catch (err) {
      console.error('Failed to fetch patients:', err);
      setPatientsError('Failed to load patients from database');
    } finally {
      setIsLoadingPatients(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, []);

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
        <>
          <Divider />
          <RecommendedPrompts
            prompts={RECOMMENDED_PROMPTS}
            onPromptClick={handlePromptClick}
          />
        </>
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
