
"""
Advanced notification system
"""
import smtplib
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
from pathlib import Path
import requests
from config.settings import settings
from utils.helpers.logger import logger

class NotificationChannel:
    """Base notification channel"""
    
    def send(self, message: Dict[str, Any]) -> bool:
        raise NotImplementedError

class EmailChannel(NotificationChannel):
    """Email notification channel"""
    
    def __init__(self):
        self.smtp_server = settings.notifications.smtp_server
        self.smtp_port = settings.notifications.smtp_port
        self.username = settings.notifications.smtp_username
        self.password = settings.notifications.smtp_password
    
    def send(self, message: Dict[str, Any]) -> bool:
        """Send email notification"""
        if not all([self.smtp_server, self.username, self.password]):
            logger.log_structured('warning', 'Email configuration incomplete')
            return False
        
        try:
            msg = MimeMultipart()
            msg['From'] = self.username
            msg['To'] = message['recipient']
            msg['Subject'] = message['subject']
            
            # Add body
            body = message.get('body', '')
            msg.attach(MimeText(body, 'plain'))
            
            # Add HTML body if provided
            if 'html_body' in message:
                msg.attach(MimeText(message['html_body'], 'html'))
            
            # Add attachments if provided
            for attachment in message.get('attachments', []):
                self._add_attachment(msg, attachment)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.log_structured('info', 'Email sent successfully', 
                                recipient=message['recipient'],
                                subject=message['subject'])
            return True
            
        except Exception as e:
            logger.log_error_with_context(e, {'message': message, 'channel': 'email'})
            return False
    
    def _add_attachment(self, msg: MimeMultipart, attachment_path: str):
        """Add attachment to email"""
        try:
            with open(attachment_path, 'rb') as attachment:
                part = MimeBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {Path(attachment_path).name}'
            )
            msg.attach(part)
        except Exception as e:
            logger.log_error_with_context(e, {'attachment_path': attachment_path})

class SlackChannel(NotificationChannel):
    """Slack notification channel"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, message: Dict[str, Any]) -> bool:
        """Send Slack notification"""
        try:
            slack_message = {
                'text': message.get('subject', 'HCE Analyzer Notification'),
                'attachments': [{
                    'color': self._get_color_for_severity(message.get('severity', 'info')),
                    'fields': [
                        {
                            'title': 'Message',
                            'value': message.get('body', ''),
                            'short': False
                        }
                    ],
                    'footer': 'HCE Analyzer Pro',
                    'ts': int(datetime.now().timestamp())
                }]
            }
            
            response = requests.post(self.webhook_url, json=slack_message)
            response.raise_for_status()
            
            logger.log_structured('info', 'Slack notification sent successfully')
            return True
            
        except Exception as e:
            logger.log_error_with_context(e, {'message': message, 'channel': 'slack'})
            return False
    
    def _get_color_for_severity(self, severity: str) -> str:
        """Get color code for severity level"""
        colors = {
            'critical': '#e74c3c',
            'high': '#f39c12',
            'medium': '#f1c40f',
            'low': '#27ae60',
            'info': '#3498db'
        }
        return colors.get(severity.lower(), '#95a5a6')

class WebhookChannel(NotificationChannel):
    """Generic webhook notification channel"""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {'Content-Type': 'application/json'}
    
    def send(self, message: Dict[str, Any]) -> bool:
        """Send webhook notification"""
        try:
            payload = {
                'timestamp': datetime.now().isoformat(),
                'source': 'hce_analyzer_pro',
                'notification': message
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            logger.log_structured('info', 'Webhook notification sent successfully',
                                webhook_url=self.webhook_url)
            return True
            
        except Exception as e:
            logger.log_error_with_context(e, {'message': message, 'channel': 'webhook'})
            return False

class NotificationService:
    """Advanced notification management service"""
    
    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self.notification_templates: Dict[str, Dict[str, str]] = {}
        self.notification_history: List[Dict[str, Any]] = []
        self._setup_default_channels()
        self._load_templates()
    
    def _setup_default_channels(self):
        """Setup default notification channels"""
        # Email channel
        if settings.notifications.smtp_server:
            self.channels['email'] = EmailChannel()
        
        # Add other channels as configured
        # self.channels['slack'] = SlackChannel(webhook_url)
        # self.channels['webhook'] = WebhookChannel(webhook_url)
    
    def _load_templates(self):
        """Load notification templates"""
        self.notification_templates = {
            'alert_critical': {
                'subject': 'CRITICAL ALERT: {title}',
                'body': '''
A critical alert has been triggered in HCE Analyzer Pro.

Alert Details:
- Type: {alert_type}
- Severity: {severity}
- Patient ID: {patient_id}
- Message: {message}
- Time: {timestamp}

Please review this alert immediately.

Best regards,
HCE Analyzer Pro System
                ''',
                'html_body': '''
<html>
<body>
    <h2 style="color: #e74c3c;">CRITICAL ALERT: {title}</h2>
    <p>A critical alert has been triggered in HCE Analyzer Pro.</p>
    
    <h3>Alert Details:</h3>
    <ul>
        <li><strong>Type:</strong> {alert_type}</li>
        <li><strong>Severity:</strong> <span style="color: #e74c3c;">{severity}</span></li>
        <li><strong>Patient ID:</strong> {patient_id}</li>
        <li><strong>Message:</strong> {message}</li>
        <li><strong>Time:</strong> {timestamp}</li>
    </ul>
    
    <p style="color: #e74c3c;"><strong>Please review this alert immediately.</strong></p>
    
    <p>Best regards,<br>HCE Analyzer Pro System</p>
</body>
</html>
                '''
            },
            'backup_completed': {
                'subject': 'Backup Completed Successfully',
                'body': '''
System backup has been completed successfully.

Backup Details:
- Backup ID: {backup_id}
- Type: {backup_type}
- Files: {files_count}
- Size: {size_mb} MB
- Duration: {duration}

The system data is now safely backed up.

Best regards,
HCE Analyzer Pro System
                '''
            },
            'analysis_complete': {
                'subject': 'Medical Analysis Complete - Patient {patient_id}',
                'body': '''
Medical analysis has been completed for patient {patient_id}.

Analysis Summary:
- Patient: {patient_name}
- Analysis Type: {analysis_type}
- Findings: {findings_count}
- Critical Issues: {critical_count}
- Completion Time: {timestamp}

Please review the results in the system dashboard.

Best regards,
HCE Analyzer Pro System
                '''
            }
        }
    
    def add_channel(self, name: str, channel: NotificationChannel):
        """Add a notification channel"""
        self.channels[name] = channel
        logger.log_structured('info', 'Notification channel added', channel_name=name)
    
    def send_notification(self, template_name: str, recipients: List[str], 
                         channels: List[str], **template_vars) -> Dict[str, Any]:
        """Send notification using template"""
        if template_name not in self.notification_templates:
            logger.log_structured('error', 'Template not found', template_name=template_name)
            return {'success': False, 'error': 'Template not found'}
        
        template = self.notification_templates[template_name]
        
        # Format template with variables
        message = {
            'subject': template['subject'].format(**template_vars),
            'body': template['body'].format(**template_vars),
            'severity': template_vars.get('severity', 'info'),
            'timestamp': datetime.now().isoformat()
        }
        
        if 'html_body' in template:
            message['html_body'] = template['html_body'].format(**template_vars)
        
        results = {}
        
        # Send through each channel
        for channel_name in channels:
            if channel_name not in self.channels:
                results[channel_name] = {'success': False, 'error': 'Channel not configured'}
                continue
            
            channel_results = []
            for recipient in recipients:
                message['recipient'] = recipient
                success = self.channels[channel_name].send(message)
                channel_results.append({'recipient': recipient, 'success': success})
            
            results[channel_name] = channel_results
        
        # Log notification
        notification_record = {
            'template': template_name,
            'recipients': recipients,
            'channels': channels,
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'template_vars': template_vars
        }
        
        self.notification_history.append(notification_record)
        
        logger.log_structured('info', 'Notification sent', 
                            template=template_name,
                            recipients_count=len(recipients),
                            channels=channels)
        
        return {'success': True, 'results': results}
    
    def send_alert_notification(self, alert: Dict[str, Any], recipients: List[str]):
        """Send alert notification"""
        template_name = 'alert_critical' if alert.get('severity') == 'critical' else 'alert_general'
        
        return self.send_notification(
            template_name=template_name,
            recipients=recipients,
            channels=['email'],  # Default to email for alerts
            title=alert.get('title', 'System Alert'),
            alert_type=alert.get('type', 'Unknown'),
            severity=alert.get('severity', 'Unknown'),
            patient_id=alert.get('patient_id', 'N/A'),
            message=alert.get('message', ''),
            timestamp=alert.get('created_at', datetime.now().isoformat())
        )
    
    def send_backup_notification(self, backup_result: Dict[str, Any], recipients: List[str]):
        """Send backup completion notification"""
        duration = 'Unknown'
        if backup_result.get('start_time') and backup_result.get('end_time'):
            start = datetime.fromisoformat(backup_result['start_time'])
            end = datetime.fromisoformat(backup_result['end_time'])
            duration = str(end - start)
        
        return self.send_notification(
            template_name='backup_completed',
            recipients=recipients,
            channels=['email'],
            backup_id=backup_result.get('backup_id', 'Unknown'),
            backup_type=backup_result.get('type', 'Unknown'),
            files_count=backup_result.get('files_backed_up', 0),
            size_mb=round(backup_result.get('total_size', 0) / (1024*1024), 2),
            duration=duration
        )
    
    def get_notification_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get notification history"""
        return sorted(self.notification_history, 
                     key=lambda x: x['timestamp'], reverse=True)[:limit]
    
    def get_notification_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get notification statistics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_notifications = [
            n for n in self.notification_history 
            if datetime.fromisoformat(n['timestamp']) >= cutoff_date
        ]
        
        stats = {
            'total_notifications': len(recent_notifications),
            'by_template': {},
            'by_channel': {},
            'success_rate': 0
        }
        
        successful_notifications = 0
        total_attempts = 0
        
        for notification in recent_notifications:
            # Count by template
            template = notification['template']
            stats['by_template'][template] = stats['by_template'].get(template, 0) + 1
            
            # Count by channel and calculate success rate
            for channel, results in notification['results'].items():
                stats['by_channel'][channel] = stats['by_channel'].get(channel, 0) + len(results)
                
                if isinstance(results, list):
                    for result in results:
                        total_attempts += 1
                        if result.get('success'):
                            successful_notifications += 1
        
        if total_attempts > 0:
            stats['success_rate'] = successful_notifications / total_attempts
        
        return stats

# Global notification service instance
notification_service = NotificationService()
