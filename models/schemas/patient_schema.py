
"""
Patient data schemas
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class PatientBase(BaseModel):
    """Base patient model"""
    patient_id: str = Field(..., description="Unique patient identifier")
    name: str = Field(..., description="Patient full name")
    age: Optional[int] = Field(None, ge=0, le=150, description="Patient age")
    gender: Optional[GenderEnum] = Field(None, description="Patient gender")
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")
    
    @validator('patient_id')
    def validate_patient_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Patient ID must be at least 3 characters long')
        return v.upper()

class PatientCreate(PatientBase):
    """Schema for creating a patient"""
    medical_record: str = Field(..., description="Initial medical record")

class PatientUpdate(BaseModel):
    """Schema for updating patient information"""
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[GenderEnum] = None
    date_of_birth: Optional[datetime] = None

class MedicalCondition(BaseModel):
    """Medical condition model"""
    condition_id: str
    name: str
    icd_code: Optional[str] = None
    severity: str = Field(default="medium")
    diagnosed_date: Optional[datetime] = None
    status: str = Field(default="active")  # active, resolved, chronic

class Medication(BaseModel):
    """Medication model"""
    medication_id: str
    name: str
    dosage: str
    frequency: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    prescribing_doctor: Optional[str] = None

class Allergy(BaseModel):
    """Allergy model"""
    allergen: str
    reaction: str
    severity: str = Field(default="medium")
    discovered_date: Optional[datetime] = None

class VitalSigns(BaseModel):
    """Vital signs model"""
    recorded_at: datetime
    blood_pressure_systolic: Optional[int] = Field(None, ge=50, le=300)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=30, le=200)
    heart_rate: Optional[int] = Field(None, ge=30, le=250)
    temperature: Optional[float] = Field(None, ge=90.0, le=110.0)
    respiratory_rate: Optional[int] = Field(None, ge=5, le=60)
    oxygen_saturation: Optional[float] = Field(None, ge=70.0, le=100.0)

class LabResult(BaseModel):
    """Laboratory result model"""
    test_name: str
    value: float
    unit: str
    reference_range: str
    status: str = Field(default="normal")  # normal, high, low, critical
    tested_at: datetime

class PatientDetail(PatientBase):
    """Detailed patient information"""
    created_at: datetime
    updated_at: datetime
    conditions: List[MedicalCondition] = []
    medications: List[Medication] = []
    allergies: List[Allergy] = []
    vital_signs: List[VitalSigns] = []
    lab_results: List[LabResult] = []
    medical_history: List[str] = []

class PatientSummary(BaseModel):
    """Patient summary for lists"""
    patient_id: str
    name: str
    age: Optional[int]
    gender: Optional[GenderEnum]
    conditions_count: int
    medications_count: int
    last_visit: Optional[datetime]
    risk_level: str = Field(default="low")

class PatientSearchRequest(BaseModel):
    """Patient search request"""
    query: Optional[str] = None
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, le=150)
    gender: Optional[GenderEnum] = None
    condition: Optional[str] = None
    limit: int = Field(default=20, le=100)
    offset: int = Field(default=0, ge=0)

class PatientSearchResponse(BaseModel):
    """Patient search response"""
    patients: List[PatientSummary]
    total_count: int
    limit: int
    offset: int
