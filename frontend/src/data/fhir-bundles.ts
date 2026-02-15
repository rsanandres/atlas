// Shared FHIR bundle map — used by ReferencePanel and ChatPanel

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FhirBundle = any;

// Original 8 personas
import larsonJson from './personas/larson.json';
import ziemeJson from './personas/zieme.json';
import christiansenJson from './personas/christiansen.json';
import hegmannJson from './personas/hegmann.json';
import herzogJson from './personas/herzog.json';
import adamJson from './personas/abbott_adam.json';
import alvaJson from './personas/abbott_alva.json';
import amayaJson from './personas/abbott_amaya.json';

// 9 data-rich example patients
import weberJson from './personas/weber.json';
import trompJson from './personas/tromp.json';
import kubJson from './personas/kub.json';
import metzJson from './personas/metz.json';
import rippinJson from './personas/rippin.json';
import danielJson from './personas/daniel.json';
import franeckiJson from './personas/franecki.json';
import larsonErichJson from './personas/larson_erich.json';
import marvinJson from './personas/marvin.json';

export const FHIR_BUNDLES: Record<string, FhirBundle> = {
  // 8 original personas
  "5e81d5b2-af01-4367-9b2e-0cdf479094a4": larsonJson,
  "616d0449-c98e-46bb-a1f6-0170499fd4e4": ziemeJson,
  "0beb6802-3353-4144-8ae3-97176bce86c3": christiansenJson,
  "6a4168a1-2cfd-4269-8139-8a4a663adfe7": hegmannJson,
  "7f7ad77a-5dd5-4df0-ba36-f4f1e4b6d368": herzogJson,
  "53fcaff1-eb44-4257-819b-50b47f311edf": adamJson,
  "f883318e-9a81-4f77-9cff-5318a00b777f": alvaJson,
  "4b7098a8-13b8-4916-a379-6ae2c8a70a8a": amayaJson,
  // 9 data-rich example patients
  "0c23c2f2-bd77-4311-a576-7829d807f2e2": weberJson,
  "a1d034a7-8e76-4b4c-806a-465bf66a0702": trompJson,
  "5fce8d66-83df-4fd9-b293-76bb5a4f43c6": kubJson,
  "2021c4b5-f560-476f-88f2-8524aae95824": metzJson,
  "887bdea7-43ce-4e17-b614-62b2be1b2c59": rippinJson,
  "a045ffdb-c70e-47b3-8d4d-041ced44f281": danielJson,
  "775775b6-95af-4049-8e23-9bc9a9e82252": franeckiJson,
  "89a8e44d-92c2-4539-83b2-755307a2e30f": larsonErichJson,
  "54d5c0ff-89de-4f65-b2a5-c5ecfaf450e8": marvinJson,
};
