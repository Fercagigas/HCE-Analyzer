
"""
Data validation utilities
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, validator
import re
from datetime import datetime

class PatientDataValidator(BaseModel):
    """Validator for patient data"""
    patient_id: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_record: str
    
    @validator('patient_id')
    def validate_patient_id(cls, v):
        if not re.match(r'^[A-Z0-9]{6,12}$', v):
            raise ValueError('Patient ID must be 6-12 alphanumeric characters')
        return v
    
    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Age must be between 0 and 150')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v is not None and v.upper() not in ['M', 'F', 'MALE', 'FEMALE', 'OTHER']:
            raise ValueError('Gender must be M, F, Male, Female, or Other')
        return v.upper() if v else v

class DataValidator:
    """Main data validation class"""
    
    @staticmethod
    def validate_medical_record(record: str) -> Dict[str, Any]:
        """Validate medical record format and content"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'score': 100
        }
        
        # Check minimum length
        if len(record) < 50:
            validation_result['errors'].append('Medical record too short')
            validation_result['score'] -= 30
        
        # Check for required sections
        required_sections = ['historia', 'examen', 'diagnóstico', 'tratamiento']
        missing_sections = []
        
        for section in required_sections:
            if section.lower() not in record.lower():
                missing_sections.append(section)
                validation_result['score'] -= 15
        
        if missing_sections:
            validation_result['warnings'].append(f'Missing sections: {", ".join(missing_sections)}')
        
        # Check for sensitive information
        sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b\d{16}\b',  # Credit card pattern
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, record):
                validation_result['warnings'].append('Potential sensitive information detected')
                break
        
        validation_result['is_valid'] = len(validation_result['errors']) == 0
        return validation_result
    
    @staticmethod
    def validate_file_upload(file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Validate uploaded file"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'file_size': len(file_content),
            'file_type': file_type
        }
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if len(file_content) > max_size:
            validation_result['errors'].append('File size exceeds 10MB limit')
            validation_result['is_valid'] = False
        
        # Check file type
        allowed_types = ['pdf', 'txt', 'docx', 'doc']
        if file_type.lower() not in allowed_types:
            validation_result['errors'].append(f'File type {file_type} not allowed')
            validation_result['is_valid'] = False
        
        return validation_result
