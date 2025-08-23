
"""
Alerts API routes
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional, List
from services.alerts.alert_service import alert_service, AlertSeverity, AlertType
from utils.helpers.logger import logger

router = APIRouter()

@router.get("/active-alerts")
async def get_active_alerts(
    request: Request,
    severity: Optional[str] = None,
    patient_id: Optional[str] = None
):
    """Get active alerts"""
    user_id = request.state.user_id
    
    try:
        severity_filter = None
        if severity:
            try:
                severity_filter = AlertSeverity(severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid severity level")
        
        alerts = alert_service.get_active_alerts(severity_filter, patient_id)
        
        # Convert alerts to dict format
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'type': alert.type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'patient_id': alert.patient_id,
                'created_at': alert.created_at.isoformat(),
                'metadata': alert.metadata
            })
        
        logger.log_user_action(user_id, 'view_active_alerts', {
            'alerts_count': len(alerts_data),
            'severity_filter': severity,
            'patient_filter': patient_id
        })
        
        return {
            'success': True,
            'alerts': alerts_data,
            'total_count': len(alerts_data)
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'operation': 'get_active_alerts'
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")

@router.post("/acknowledge-alert/{alert_id}")
async def acknowledge_alert(
    request: Request,
    alert_id: str
):
    """Acknowledge an alert"""
    user_id = request.state.user_id
    
    try:
        success = alert_service.acknowledge_alert(alert_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        logger.log_user_action(user_id, 'acknowledge_alert', {
            'alert_id': alert_id
        })
        
        return {
            'success': True,
            'message': 'Alert acknowledged successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'alert_id': alert_id,
            'operation': 'acknowledge_alert'
        })
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")

@router.get("/alert-statistics")
async def get_alert_statistics(
    request: Request,
    days: int = 30
):
    """Get alert statistics"""
    user_id = request.state.user_id
    
    try:
        stats = alert_service.get_alert_statistics(days)
        
        logger.log_user_action(user_id, 'view_alert_statistics', {
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
            'operation': 'get_alert_statistics'
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")

@router.post("/create-alert")
async def create_custom_alert(
    request: Request,
    alert_data: Dict[str, Any]
):
    """Create a custom alert"""
    user_id = request.state.user_id
    
    try:
        alert_type = AlertType(alert_data.get('type', 'system_error'))
        severity = AlertSeverity(alert_data.get('severity', 'medium'))
        title = alert_data.get('title', 'Custom Alert')
        message = alert_data.get('message', '')
        
        alert = alert_service.create_alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            user_id=user_id,
            patient_id=alert_data.get('patient_id'),
            metadata=alert_data.get('metadata', {})
        )
        
        return {
            'success': True,
            'alert_id': alert.id,
            'message': 'Alert created successfully'
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'operation': 'create_custom_alert'
        })
        raise HTTPException(status_code=500, detail="Failed to create alert")
