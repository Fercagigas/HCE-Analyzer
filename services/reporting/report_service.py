
"""
Advanced reporting service
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json
from utils.formatters.report_formatter import ReportFormatter
from utils.helpers.logger import logger

class ReportService:
    """Advanced medical reporting service"""
    
    def __init__(self):
        self.formatter = ReportFormatter()
        self.reports_dir = Path("data/exports/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_patient_summary_report(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive patient summary report"""
        logger.log_structured('info', 'Generating patient summary report', 
                            patient_id=patient_data.get('patient_id'))
        
        report_data = {
            'report_type': 'patient_summary',
            'generated_at': datetime.now().isoformat(),
            'patient_info': {
                'id': patient_data.get('patient_id'),
                'name': patient_data.get('name'),
                'age': patient_data.get('age'),
                'gender': patient_data.get('gender')
            },
            'medical_history': self._analyze_medical_history(patient_data.get('history', [])),
            'current_conditions': patient_data.get('conditions', []),
            'medications': patient_data.get('medications', []),
            'allergies': patient_data.get('allergies', []),
            'risk_factors': self._calculate_risk_factors(patient_data),
            'recommendations': self._generate_recommendations(patient_data),
            'charts': self._generate_patient_charts(patient_data)
        }
        
        return self.formatter.format_medical_analysis(report_data)
    
    def generate_analytics_dashboard_data(self, date_range: int = 30) -> Dict[str, Any]:
        """Generate data for analytics dashboard"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=date_range)
        
        # Mock data - in real implementation, this would query the database
        dashboard_data = {
            'summary_stats': {
                'total_patients': 1250,
                'total_analyses': 3420,
                'critical_alerts': 45,
                'avg_processing_time': 2.3
            },
            'trends': {
                'daily_analyses': self._generate_trend_data(date_range),
                'condition_distribution': self._generate_condition_distribution(),
                'severity_breakdown': self._generate_severity_breakdown()
            },
            'performance_metrics': {
                'accuracy_score': 0.94,
                'processing_speed': 1.8,
                'user_satisfaction': 4.6
            },
            'alerts_summary': {
                'critical': 12,
                'high': 28,
                'medium': 67,
                'low': 134
            }
        }
        
        return dashboard_data
    
    def _analyze_medical_history(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patient medical history"""
        if not history:
            return {'total_entries': 0, 'patterns': [], 'timeline': []}
        
        # Analyze patterns in medical history
        conditions = [entry.get('condition', '') for entry in history]
        condition_counts = pd.Series(conditions).value_counts().to_dict()
        
        return {
            'total_entries': len(history),
            'most_common_conditions': dict(list(condition_counts.items())[:5]),
            'timeline': sorted(history, key=lambda x: x.get('date', ''), reverse=True)[:10],
            'patterns': self._identify_medical_patterns(history)
        }
    
    def _calculate_risk_factors(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate patient risk factors"""
        risk_factors = []
        
        age = patient_data.get('age', 0)
        conditions = patient_data.get('conditions', [])
        medications = patient_data.get('medications', [])
        
        # Age-based risks
        if age > 65:
            risk_factors.append({
                'factor': 'Advanced Age',
                'risk_level': 'medium',
                'description': 'Increased risk for age-related conditions'
            })
        
        # Condition-based risks
        high_risk_conditions = ['diabetes', 'hypertension', 'heart disease']
        for condition in conditions:
            if any(risk_cond in condition.lower() for risk_cond in high_risk_conditions):
                risk_factors.append({
                    'factor': f'Existing {condition}',
                    'risk_level': 'high',
                    'description': f'Complications related to {condition}'
                })
        
        # Medication interactions
        if len(medications) > 5:
            risk_factors.append({
                'factor': 'Polypharmacy',
                'risk_level': 'medium',
                'description': 'Multiple medications increase interaction risk'
            })
        
        return risk_factors
    
    def _generate_recommendations(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate personalized recommendations"""
        recommendations = []
        
        age = patient_data.get('age', 0)
        conditions = patient_data.get('conditions', [])
        
        # Age-based recommendations
        if age > 50:
            recommendations.append({
                'category': 'Preventive Care',
                'recommendation': 'Annual comprehensive health screening',
                'priority': 'high',
                'frequency': 'yearly'
            })
        
        # Condition-specific recommendations
        if any('diabetes' in cond.lower() for cond in conditions):
            recommendations.append({
                'category': 'Diabetes Management',
                'recommendation': 'Regular HbA1c monitoring',
                'priority': 'high',
                'frequency': 'quarterly'
            })
        
        return recommendations
    
    def _generate_patient_charts(self, patient_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate charts for patient data"""
        charts = {}
        
        # Vital signs trend (mock data)
        dates = pd.date_range(start='2024-01-01', end='2024-08-17', freq='W')
        bp_systolic = [120 + i*2 + (i%3)*5 for i in range(len(dates))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=bp_systolic, name='Systolic BP'))
        fig.update_layout(title='Blood Pressure Trend', xaxis_title='Date', yaxis_title='mmHg')
        charts['bp_trend'] = fig.to_json()
        
        # Condition distribution
        conditions = patient_data.get('conditions', ['Hypertension', 'Diabetes', 'Arthritis'])
        fig_pie = px.pie(values=[1]*len(conditions), names=conditions, title='Current Conditions')
        charts['conditions_pie'] = fig_pie.to_json()
        
        return charts
    
    def _generate_trend_data(self, days: int) -> List[Dict[str, Any]]:
        """Generate trend data for dashboard"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                             end=datetime.now(), freq='D')
        
        trend_data = []
        for i, date in enumerate(dates):
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'analyses': 50 + i*2 + (i%7)*10,
                'patients': 20 + i + (i%5)*3
            })
        
        return trend_data
    
    def _generate_condition_distribution(self) -> List[Dict[str, Any]]:
        """Generate condition distribution data"""
        return [
            {'condition': 'Hypertension', 'count': 245, 'percentage': 19.6},
            {'condition': 'Diabetes', 'count': 198, 'percentage': 15.8},
            {'condition': 'Arthritis', 'count': 156, 'percentage': 12.5},
            {'condition': 'Heart Disease', 'count': 134, 'percentage': 10.7},
            {'condition': 'COPD', 'count': 89, 'percentage': 7.1}
        ]
    
    def _generate_severity_breakdown(self) -> List[Dict[str, Any]]:
        """Generate severity breakdown data"""
        return [
            {'severity': 'Critical', 'count': 12, 'color': '#e74c3c'},
            {'severity': 'High', 'count': 28, 'color': '#f39c12'},
            {'severity': 'Medium', 'count': 67, 'color': '#f1c40f'},
            {'severity': 'Low', 'count': 134, 'color': '#27ae60'}
        ]
    
    def _identify_medical_patterns(self, history: List[Dict[str, Any]]) -> List[str]:
        """Identify patterns in medical history"""
        patterns = []
        
        if len(history) > 5:
            patterns.append("Frequent medical visits pattern detected")
        
        conditions = [entry.get('condition', '') for entry in history]
        if len(set(conditions)) < len(conditions) * 0.7:
            patterns.append("Recurring condition pattern identified")
        
        return patterns
    
    def export_report(self, report_data: Dict[str, Any], format_type: str = 'json') -> str:
        """Export report to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{timestamp}.{format_type}"
        file_path = self.reports_dir / filename
        
        if format_type == 'json':
            self.formatter.export_to_json(report_data, str(file_path))
        elif format_type == 'html':
            html_content = self.formatter.generate_html_report(report_data)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        logger.log_structured('info', 'Report exported', 
                            file_path=str(file_path), format=format_type)
        
        return str(file_path)
