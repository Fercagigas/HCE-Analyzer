
"""
Reports API routes
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from services.reporting.report_service import ReportService
from utils.helpers.logger import logger

router = APIRouter()
report_service = ReportService()

@router.post("/generate-patient-report")
async def generate_patient_report(
    request: Request,
    background_tasks: BackgroundTasks,
    report_data: Dict[str, Any]
):
    """Generate comprehensive patient report"""
    user_id = request.state.user_id
    patient_id = report_data.get('patient_id')
    
    if not patient_id:
        raise HTTPException(status_code=400, detail="Patient ID is required")
    
    logger.log_user_action(user_id, 'generate_patient_report', {
        'patient_id': patient_id
    })
    
    try:
        # Generate report
        report = report_service.generate_patient_summary_report(report_data)
        
        # Export report in background
        background_tasks.add_task(
            report_service.export_report,
            report,
            'html'
        )
        
        return {
            'success': True,
            'report': report,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'patient_id': patient_id,
            'operation': 'generate_patient_report'
        })
        raise HTTPException(status_code=500, detail="Report generation failed")

@router.get("/dashboard-data")
async def get_dashboard_data(
    request: Request,
    days: int = 30
):
    """Get dashboard analytics data"""
    user_id = request.state.user_id
    
    try:
        dashboard_data = report_service.generate_analytics_dashboard_data(days)
        
        logger.log_user_action(user_id, 'view_dashboard', {
            'period_days': days
        })
        
        return {
            'success': True,
            'dashboard_data': dashboard_data,
            'period_days': days
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'operation': 'get_dashboard_data'
        })
        raise HTTPException(status_code=500, detail="Failed to load dashboard data")

@router.post("/export-report")
async def export_report(
    request: Request,
    export_data: Dict[str, Any]
):
    """Export report to file"""
    user_id = request.state.user_id
    report_data = export_data.get('report_data')
    format_type = export_data.get('format', 'json')
    
    if not report_data:
        raise HTTPException(status_code=400, detail="Report data is required")
    
    if format_type not in ['json', 'html', 'pdf']:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    try:
        file_path = report_service.export_report(report_data, format_type)
        
        logger.log_user_action(user_id, 'export_report', {
            'format': format_type,
            'file_path': file_path
        })
        
        return FileResponse(
            path=file_path,
            filename=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}",
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'format': format_type,
            'operation': 'export_report'
        })
        raise HTTPException(status_code=500, detail="Report export failed")

@router.get("/report-templates")
async def get_report_templates(request: Request):
    """Get available report templates"""
    user_id = request.state.user_id
    
    templates = [
        {
            'id': 'patient_summary',
            'name': 'Patient Summary Report',
            'description': 'Comprehensive patient overview with medical history',
            'fields': ['patient_info', 'conditions', 'medications', 'allergies']
        },
        {
            'id': 'analysis_report',
            'name': 'Medical Analysis Report',
            'description': 'Detailed analysis results with findings and recommendations',
            'fields': ['analysis_results', 'findings', 'recommendations', 'risk_assessment']
        },
        {
            'id': 'trend_analysis',
            'name': 'Trend Analysis Report',
            'description': 'Patient health trends over time',
            'fields': ['vital_signs', 'lab_results', 'medication_changes']
        }
    ]
    
    logger.log_user_action(user_id, 'view_report_templates')
    
    return {
        'success': True,
        'templates': templates
    }
