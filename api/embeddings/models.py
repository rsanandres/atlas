"""Request/Response models for embeddings service."""

from pydantic import BaseModel, Field


class ClinicalNote(BaseModel):
    id: str
    fullUrl: str = Field(default="", alias="fullUrl")
    resourceType: str
    content: str = Field(min_length=1)  # Ensure content is not empty
    patient_id: str = Field(default="unknown", alias="patientId")
    resourceJson: str = Field(default="", alias="resourceJson")  # Optional: original JSON for RecursiveJsonSplitter
    sourceFile: str = Field(default="", alias="sourceFile")  # Source file path
