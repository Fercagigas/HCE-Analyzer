
"""
Analysis API routes
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from models.schemas.patient_schema import PatientDetail
from services.rag_service import RAGService
from services.clinical_chat import ClinicalChatService
from services.alerts.alert_service import alert_service
from utils.validators.data_validator import DataValidator
from utils.helpers.logger import logger
from utils.helpers.cache import cache_manager

router = APIRouter()

# Initialize services (these would be properly injected in production)
rag_service = RAGService()
chat_service = ClinicalChatService()
validator = DataValidator()

@router.post("/upload-document")
async def upload_medical_document(
    request: Request,
    file: UploadFile = File(...),
    patient_id: Optional[str] = None
):
    """Upload and process medical document"""
    user_id = request.state.user_id
    
    # Validate file
    file_content = await file.read()
    file_validation = validator.validate_file_upload(file_content, file.filename.split('.')[-1])
    
    if not file_validation['is_valid']:
        raise HTTPException(status_code=400, detail=file_validation['errors'])
    
    logger.log_user_action(user_id, 'document_upload', {
        'filename': file.filename,
        'file_size': len(file_content),
        'patient_id': patient_id
    })
    
    try:
        # Process document
        processing_result = await rag_service.process_document(
            file_content, 
            file.filename,
            patient_id
        )
        
        return {
            'success': True,
            'document_id': processing_result['document_id'],
            'processing_status': processing_result['status'],
            'extracted_text_length': len(processing_result.get('text', '')),
            'metadata': processing_result.get('metadata', {})
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'filename': file.filename,
            'patient_id': patient_id
        })
        raise HTTPException(status_code=500, detail="Document processing failed")

@router.post("/analyze-medical-record")
async def analyze_medical_record(
    request: Request,
    patient_data: Dict[str, Any]
):
    """Analyze medical record using AI"""
    user_id = request.state.user_id
    patient_id = patient_data.get('patient_id')
    
    # Validate medical record
    record_validation = validator.validate_medical_record(
        patient_data.get('medical_record', '')
    )
    
    if not record_validation['is_valid']:
        raise HTTPException(status_code=400, detail=record_validation['errors'])
    
    # Check cache first
    document_hash = hash(patient_data.get('medical_record', ''))
    cached_result = cache_manager.get_cached_analysis(patient_id, str(document_hash))
    
    if cached_result:
        logger.log_structured('info', 'Analysis served from cache', 
                            patient_id=patient_id, user_id=user_id)
        return cached_result
    
    logger.log_analysis_request(user_id, patient_id, 'medical_record')
    
    try:
        # Perform analysis
        analysis_result = await rag_service.analyze_medical_record(patient_data)
        
        # Check for alerts
        triggered_alerts = alert_service.evaluate_alert_rules(patient_data)
        if triggered_alerts:
            analysis_result['alerts'] = [
                {
                    'id': alert.id,
                    'type': alert.type.value,
                    'severity': alert.severity.value,
                    'message': alert.message
                }
                for alert in triggered_alerts
            ]
        
        # Cache result
        cache_manager.cache_analysis_result(patient_id, str(document_hash), analysis_result)
        
        logger.log_structured('info', 'Medical record analysis completed',
                            patient_id=patient_id,
                            findings_count=len(analysis_result.get('findings', [])),
                            alerts_count=len(triggered_alerts))
        
        return {
            'success': True,
            'analysis': analysis_result,
            'validation_score': record_validation['score'],
            'processing_time': analysis_result.get('processing_time', 0)
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'patient_id': patient_id,
            'operation': 'medical_record_analysis'
        })
        raise HTTPException(status_code=500, detail="Analysis failed")

@router.post("/clinical-chat")
async def clinical_chat(
    request: Request,
    chat_data: Dict[str, Any]
):
    """Clinical chat with AI assistant"""
    user_id = request.state.user_id
    message = chat_data.get('message', '')
    patient_context = chat_data.get('patient_context', {})
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    logger.log_user_action(user_id, 'clinical_chat', {
        'message_length': len(message),
        'has_patient_context': bool(patient_context)
    })
    
    try:
        # Get chat response
        chat_response = await chat_service.get_clinical_response(
            message, 
            patient_context,
            user_id
        )
        
        return {
            'success': True,
            'response': chat_response['response'],
            'confidence': chat_response.get('confidence', 0.0),
            'sources': chat_response.get('sources', []),
            'suggestions': chat_response.get('suggestions', [])
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'message': message[:100],  # Log first 100 chars only
            'operation': 'clinical_chat'
        })
        raise HTTPException(status_code=500, detail="Chat service failed")

@router.get("/analysis-history/{patient_id}")
async def get_analysis_history(
    request: Request,
    patient_id: str,
    limit: int = 20,
    offset: int = 0
):
    """Get analysis history for a patient"""
    user_id = request.state.user_id
    
    try:
        # This would query the database in a real implementation
        history = await rag_service.get_patient_analysis_history(
            patient_id, limit, offset
        )
        
        logger.log_user_action(user_id, 'view_analysis_history', {
            'patient_id': patient_id,
            'results_count': len(history)
        })
        
        return {
            'success': True,
            'history': history,
            'total_count': len(history),
            'limit': limit,
            'offset': offset
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'patient_id': patient_id,
            'operation': 'get_analysis_history'
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve history")

@router.post("/batch-analyze")
async def batch_analyze_records(
    request: Request,
    batch_data: Dict[str, Any]
):
    """Batch analyze multiple medical records"""
    user_id = request.state.user_id
    records = batch_data.get('records', [])
    
    if not records or len(records) > 10:  # Limit batch size
        raise HTTPException(
            status_code=400, 
            detail="Batch must contain 1-10 records"
        )
    
    logger.log_user_action(user_id, 'batch_analysis', {
        'records_count': len(records)
    })
    
    try:
        # Process records concurrently
        analysis_tasks = [
            rag_service.analyze_medical_record(record)
            for record in records
        ]
        
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Process results
        successful_analyses = []
        failed_analyses = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_analyses.append({
                    'index': i,
                    'patient_id': records[i].get('patient_id', 'unknown'),
                    'error': str(result)
                })
            else:
                successful_analyses.append({
                    'index': i,
                    'patient_id': records[i].get('patient_id', 'unknown'),
                    'analysis': result
                })
        
        logger.log_structured('info', 'Batch analysis completed',
                            user_id=user_id,
                            successful_count=len(successful_analyses),
                            failed_count=len(failed_analyses))
        
        return {
            'success': True,
            'successful_analyses': successful_analyses,
            'failed_analyses': failed_analyses,
            'total_processed': len(records)
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'records_count': len(records),
            'operation': 'batch_analyze'
        })
        raise HTTPException(status_code=500, detail="Batch analysis failed")

@router.get("/analysis-stats")
async def get_analysis_statistics(
    request: Request,
    days: int = 30
):
    """Get analysis statistics"""
    user_id = request.state.user_id
    
    try:
        # This would query the database for real statistics
        stats = {
            'total_analyses': 1250,
            'analyses_this_period': 340,
            'average_processing_time': 2.3,
            'most_common_conditions': [
                {'condition': 'Hypertension', 'count': 89},
                {'condition': 'Diabetes', 'count': 67},
                {'condition': 'Arthritis', 'count': 45}
            ],
            'accuracy_metrics': {
                'overall_accuracy': 0.94,
                'precision': 0.92,
                'recall': 0.89
            },
            'user_satisfaction': 4.6
        }
        
        logger.log_user_action(user_id, 'view_analysis_stats', {
            'period_days': days
        })
        
        return {
            'success': True,
            'statistics': stats,
            'period_days': days
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'operation': 'get_analysis_stats'
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")
