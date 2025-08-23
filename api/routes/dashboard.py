
"""
Dashboard API routes
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from services.reporting.report_service import ReportService
from services.alerts.alert_service import alert_service
from utils.helpers.logger import logger

router = APIRouter()
report_service = ReportService()

@router.get("/overview")
async def get_dashboard_overview(
    request: Request,
    days: int = 30
):
    """Get dashboard overview data"""
    user_id = request.state.user_id
    
    try:
        # Get various metrics
        dashboard_data = report_service.generate_analytics_dashboard_data(days)
        alert_stats = alert_service.get_alert_statistics(days)
        
        overview = {
            'summary_stats': dashboard_data['summary_stats'],
            'alert_summary': alert_stats['by_severity'],
            'recent_trends': dashboard_data['trends']['daily_analyses'][-7:],  # Last 7 days
            'system_health': {
                'status': 'healthy',
                'uptime': '99.9%',
                'last_backup': '2024-08-17T10:30:00Z',
                'active_users': 45
            },
            'quick_actions': [
                {'action': 'new_analysis', 'label': 'New Analysis', 'count': 0},
                {'action': 'pending_alerts', 'label': 'Pending Alerts', 'count': alert_stats['total_alerts']},
                {'action': 'recent_reports', 'label': 'Recent Reports', 'count': 12}
            ]
        }
        
        logger.log_user_action(user_id, 'view_dashboard_overview', {
            'period_days': days
        })
        
        return {
            'success': True,
            'overview': overview,
            'period_days': days
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'operation': 'get_dashboard_overview'
        })
        raise HTTPException(status_code=500, detail="Failed to load dashboard overview")

@router.get("/analytics")
async def get_analytics_data(
    request: Request,
    metric: str,
    days: int = 30
):
    """Get specific analytics data"""
    user_id = request.state.user_id
    
    valid_metrics = [
        'patient_trends', 'condition_analysis', 'medication_patterns',
        'alert_patterns', 'user_activity', 'system_performance'
    ]
    
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail="Invalid metric type")
    
    try:
        dashboard_data = report_service.generate_analytics_dashboard_data(days)
        
        # Extract specific metric data
        if metric == 'patient_trends':
            data = dashboard_data['trends']['daily_analyses']
        elif metric == 'condition_analysis':
            data = dashboard_data['trends']['condition_distribution']
        elif metric == 'alert_patterns':
            alert_stats = alert_service.get_alert_statistics(days)
            data = alert_stats['by_type']
        else:
            # Mock data for other metrics
            data = {'message': f'Analytics for {metric} not yet implemented'}
        
        logger.log_user_action(user_id, 'view_analytics', {
            'metric': metric,
            'period_days': days
        })
        
        return {
            'success': True,
            'metric': metric,
            'data': data,
            'period_days': days
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'metric': metric,
            'operation': 'get_analytics_data'
        })
        raise HTTPException(status_code=500, detail="Failed to load analytics data")

@router.get("/recent-activity")
async def get_recent_activity(
    request: Request,
    limit: int = 20
):
    """Get recent system activity"""
    user_id = request.state.user_id
    
    try:
        # Mock recent activity data
        activities = [
            {
                'id': f'activity_{i}',
                'type': 'analysis_completed',
                'description': f'Medical analysis completed for patient P{1000+i}',
                'user': f'user_{i%5}',
                'timestamp': (datetime.now() - timedelta(hours=i)).isoformat(),
                'status': 'success'
            }
            for i in range(limit)
        ]
        
        logger.log_user_action(user_id, 'view_recent_activity', {
            'limit': limit
        })
        
        return {
            'success': True,
            'activities': activities,
            'total_count': len(activities)
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'operation': 'get_recent_activity'
        })
        raise HTTPException(status_code=500, detail="Failed to load recent activity")

@router.get("/system-status")
async def get_system_status(request: Request):
    """Get system status information"""
    user_id = request.state.user_id
    
    try:
        # Mock system status
        status = {
            'overall_status': 'healthy',
            'services': {
                'api': {'status': 'healthy', 'response_time': '45ms'},
                'database': {'status': 'healthy', 'connections': 12},
                'ai_service': {'status': 'healthy', 'queue_size': 3},
                'backup_service': {'status': 'healthy', 'last_backup': '2024-08-17T10:30:00Z'}
            },
            'resources': {
                'cpu_usage': '23%',
                'memory_usage': '67%',
                'disk_usage': '45%',
                'network_io': '1.2 MB/s'
            },
            'uptime': '15 days, 8 hours',
            'version': '2.0.0'
        }
        
        logger.log_user_action(user_id, 'view_system_status')
        
        return {
            'success': True,
            'status': status
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'operation': 'get_system_status'
        })
        raise HTTPException(status_code=500, detail="Failed to load system status")
