
"""
Advanced alert and notification system
"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from dataclasses import dataclass
from utils.helpers.logger import logger

class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertType(Enum):
    MEDICAL_EMERGENCY = "medical_emergency"
    DRUG_INTERACTION = "drug_interaction"
    ABNORMAL_VALUES = "abnormal_values"
    MISSING_DATA = "missing_data"
    SYSTEM_ERROR = "system_error"
    SECURITY_BREACH = "security_breach"

@dataclass
class Alert:
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    patient_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

class AlertService:
    """Advanced alert management system"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_handlers: Dict[AlertType, List[Callable]] = {}
        self.notification_channels: List[Callable] = []
        self.alert_rules: List[Dict[str, Any]] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules"""
        self.alert_rules = [
            {
                'name': 'Critical Lab Values',
                'condition': lambda data: self._check_critical_lab_values(data),
                'alert_type': AlertType.MEDICAL_EMERGENCY,
                'severity': AlertSeverity.CRITICAL
            },
            {
                'name': 'Drug Interactions',
                'condition': lambda data: self._check_drug_interactions(data),
                'alert_type': AlertType.DRUG_INTERACTION,
                'severity': AlertSeverity.HIGH
            },
            {
                'name': 'Missing Critical Data',
                'condition': lambda data: self._check_missing_critical_data(data),
                'alert_type': AlertType.MISSING_DATA,
                'severity': AlertSeverity.MEDIUM
            }
        ]
    
    def create_alert(self, alert_type: AlertType, severity: AlertSeverity, 
                    title: str, message: str, **kwargs) -> Alert:
        """Create a new alert"""
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.alerts)}"
        
        alert = Alert(
            id=alert_id,
            type=alert_type,
            severity=severity,
            title=title,
            message=message,
            **kwargs
        )
        
        self.alerts.append(alert)
        
        # Log alert creation
        logger.log_structured('warning', 'Alert created', 
                            alert_id=alert_id, 
                            alert_type=alert_type.value,
                            severity=severity.value,
                            patient_id=kwargs.get('patient_id'))
        
        # Trigger alert handlers
        self._trigger_alert_handlers(alert)
        
        return alert
    
    def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = user_id
                alert.acknowledged_at = datetime.now()
                
                logger.log_user_action(user_id, 'alert_acknowledged', 
                                     {'alert_id': alert_id})
                return True
        return False
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None,
                         patient_id: Optional[str] = None) -> List[Alert]:
        """Get active (unacknowledged) alerts"""
        active_alerts = [alert for alert in self.alerts if not alert.acknowledged]
        
        if severity_filter:
            active_alerts = [alert for alert in active_alerts 
                           if alert.severity == severity_filter]
        
        if patient_id:
            active_alerts = [alert for alert in active_alerts 
                           if alert.patient_id == patient_id]
        
        return sorted(active_alerts, key=lambda x: x.created_at, reverse=True)
    
    def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get alert statistics for the specified period"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_alerts = [alert for alert in self.alerts if alert.created_at >= cutoff_date]
        
        stats = {
            'total_alerts': len(recent_alerts),
            'by_severity': {},
            'by_type': {},
            'acknowledged_rate': 0,
            'avg_response_time': 0
        }
        
        # Count by severity
        for severity in AlertSeverity:
            count = len([alert for alert in recent_alerts if alert.severity == severity])
            stats['by_severity'][severity.value] = count
        
        # Count by type
        for alert_type in AlertType:
            count = len([alert for alert in recent_alerts if alert.type == alert_type])
            stats['by_type'][alert_type.value] = count
        
        # Calculate acknowledgment rate
        acknowledged_alerts = [alert for alert in recent_alerts if alert.acknowledged]
        if recent_alerts:
            stats['acknowledged_rate'] = len(acknowledged_alerts) / len(recent_alerts)
        
        # Calculate average response time
        response_times = []
        for alert in acknowledged_alerts:
            if alert.acknowledged_at:
                response_time = (alert.acknowledged_at - alert.created_at).total_seconds()
                response_times.append(response_time)
        
        if response_times:
            stats['avg_response_time'] = sum(response_times) / len(response_times)
        
        return stats
    
    def register_alert_handler(self, alert_type: AlertType, handler: Callable):
        """Register a handler for specific alert types"""
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)
    
    def add_notification_channel(self, channel: Callable):
        """Add a notification channel"""
        self.notification_channels.append(channel)
    
    def evaluate_alert_rules(self, data: Dict[str, Any]) -> List[Alert]:
        """Evaluate data against alert rules"""
        triggered_alerts = []
        
        for rule in self.alert_rules:
            try:
                if rule['condition'](data):
                    alert = self.create_alert(
                        alert_type=rule['alert_type'],
                        severity=rule['severity'],
                        title=f"Alert: {rule['name']}",
                        message=f"Rule '{rule['name']}' triggered for patient data",
                        patient_id=data.get('patient_id'),
                        metadata={'rule_name': rule['name'], 'data_snapshot': data}
                    )
                    triggered_alerts.append(alert)
            except Exception as e:
                logger.log_error_with_context(e, {'rule': rule['name'], 'data': data})
        
        return triggered_alerts
    
    def _trigger_alert_handlers(self, alert: Alert):
        """Trigger registered handlers for an alert"""
        handlers = self.alert_handlers.get(alert.type, [])
        
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.log_error_with_context(e, {'alert_id': alert.id, 'handler': str(handler)})
        
        # Send notifications through all channels
        for channel in self.notification_channels:
            try:
                channel(alert)
            except Exception as e:
                logger.log_error_with_context(e, {'alert_id': alert.id, 'channel': str(channel)})
    
    def _check_critical_lab_values(self, data: Dict[str, Any]) -> bool:
        """Check for critical laboratory values"""
        lab_values = data.get('lab_values', {})
        
        critical_ranges = {
            'glucose': (70, 400),  # mg/dL
            'systolic_bp': (90, 180),  # mmHg
            'heart_rate': (60, 100),  # bpm
            'temperature': (96.8, 100.4)  # °F
        }
        
        for test, (min_val, max_val) in critical_ranges.items():
            if test in lab_values:
                value = lab_values[test]
                if value < min_val or value > max_val:
                    return True
        
        return False
    
    def _check_drug_interactions(self, data: Dict[str, Any]) -> bool:
        """Check for potential drug interactions"""
        medications = data.get('medications', [])
        
        # Simplified interaction check
        high_risk_combinations = [
            ('warfarin', 'aspirin'),
            ('metformin', 'contrast'),
            ('digoxin', 'furosemide')
        ]
        
        med_names = [med.lower() for med in medications]
        
        for drug1, drug2 in high_risk_combinations:
            if drug1 in med_names and drug2 in med_names:
                return True
        
        return False
    
    def _check_missing_critical_data(self, data: Dict[str, Any]) -> bool:
        """Check for missing critical patient data"""
        required_fields = ['patient_id', 'age', 'gender', 'primary_diagnosis']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return True
        
        return False

# Global alert service instance
alert_service = AlertService()
