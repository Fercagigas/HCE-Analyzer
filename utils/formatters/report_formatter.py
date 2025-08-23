
"""
Report formatting utilities
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

class ReportFormatter:
    """Advanced report formatting class"""
    
    def __init__(self):
        self.templates_path = Path(__file__).parent / "templates"
    
    def format_medical_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format medical analysis for reporting"""
        formatted_report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'report_type': 'medical_analysis',
                'version': '2.0.0'
            },
            'patient_info': analysis_data.get('patient_info', {}),
            'analysis_summary': {
                'total_findings': len(analysis_data.get('findings', [])),
                'critical_alerts': len([f for f in analysis_data.get('findings', []) 
                                      if f.get('severity') == 'critical']),
                'recommendations_count': len(analysis_data.get('recommendations', []))
            },
            'detailed_analysis': analysis_data.get('analysis', ''),
            'findings': self._format_findings(analysis_data.get('findings', [])),
            'recommendations': analysis_data.get('recommendations', []),
            'risk_assessment': analysis_data.get('risk_assessment', {}),
            'follow_up': analysis_data.get('follow_up', [])
        }
        
        return formatted_report
    
    def _format_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format medical findings"""
        formatted_findings = []
        
        for finding in findings:
            formatted_finding = {
                'id': finding.get('id', ''),
                'category': finding.get('category', 'general'),
                'severity': finding.get('severity', 'low'),
                'description': finding.get('description', ''),
                'evidence': finding.get('evidence', ''),
                'confidence_score': finding.get('confidence', 0.0),
                'icd_codes': finding.get('icd_codes', []),
                'recommendations': finding.get('recommendations', [])
            }
            formatted_findings.append(formatted_finding)
        
        return sorted(formatted_findings, key=lambda x: x['severity'], reverse=True)
    
    def generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML report"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>HCE Analyzer Pro - Medical Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #2c3e50; color: white; padding: 20px; }
                .section { margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; }
                .finding { background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .critical { border-left-color: #e74c3c; }
                .high { border-left-color: #f39c12; }
                .medium { border-left-color: #f1c40f; }
                .low { border-left-color: #27ae60; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Medical Analysis Report</h1>
                <p>Generated: {generated_at}</p>
            </div>
            
            <div class="section">
                <h2>Analysis Summary</h2>
                <p>Total Findings: {total_findings}</p>
                <p>Critical Alerts: {critical_alerts}</p>
                <p>Recommendations: {recommendations_count}</p>
            </div>
            
            <div class="section">
                <h2>Detailed Analysis</h2>
                <p>{detailed_analysis}</p>
            </div>
            
            <div class="section">
                <h2>Findings</h2>
                {findings_html}
            </div>
        </body>
        </html>
        """
        
        findings_html = ""
        for finding in report_data.get('findings', []):
            findings_html += f"""
            <div class="finding {finding['severity']}">
                <h4>{finding['category'].title()}</h4>
                <p><strong>Severity:</strong> {finding['severity'].title()}</p>
                <p><strong>Description:</strong> {finding['description']}</p>
                <p><strong>Confidence:</strong> {finding['confidence_score']:.2%}</p>
            </div>
            """
        
        return html_template.format(
            generated_at=report_data['metadata']['generated_at'],
            total_findings=report_data['analysis_summary']['total_findings'],
            critical_alerts=report_data['analysis_summary']['critical_alerts'],
            recommendations_count=report_data['analysis_summary']['recommendations_count'],
            detailed_analysis=report_data['detailed_analysis'],
            findings_html=findings_html
        )
    
    def export_to_json(self, report_data: Dict[str, Any], file_path: str) -> bool:
        """Export report to JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
