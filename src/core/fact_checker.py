from typing import List, Dict, Any, Optional
import re
from datetime import datetime
from src.api.gemini_client import GeminiClient
from src.utils.file_parser import FileParser, SlideContent
from pydantic import BaseModel
import json


class FactIssue(BaseModel):
    type: str  # date_error, numerical_error, technical_claim, citation_error, knowledge_consistency
    severity: str  # high, medium, low
    original_text: str
    issue_description: str
    correct_information: Optional[str] = None
    confidence: float
    slide_number: int


class FactCheckResult(BaseModel):
    slide_number: int
    status: str  # ok, issues_found, error
    issues: List[FactIssue]
    summary: str
    token_usage: Optional[Dict[str, Any]] = None


class FactCheckReport(BaseModel):
    file_metadata: Dict[str, Any]
    total_slides: int
    slides_with_issues: int
    total_issues: int
    issues_by_type: Dict[str, int]
    issues_by_severity: Dict[str, int]
    results: List[FactCheckResult]
    total_cost_estimate: float
    timestamp: str


class FactChecker:
    def __init__(self, gemini_api_key: Optional[str] = None):
        self.file_parser = FileParser()
        self.gemini_client = GeminiClient(api_key=gemini_api_key)
        
        # Patterns for common fact-checking targets
        self.date_pattern = re.compile(r'\b(19|20)\d{2}年?\b')
        self.number_pattern = re.compile(r'\b\d+\.?\d*[KMBTG]?[Bb]?\b')
        self.percentage_pattern = re.compile(r'\b\d+\.?\d*\s*[%％]\b')
        
    def check_presentation(self, file_path: str) -> FactCheckReport:
        # Extract metadata
        metadata = self.file_parser.extract_metadata(file_path)
        
        # Parse slides
        slides = self.file_parser.parse_file(file_path)
        
        # Prepare slide data for batch checking
        slides_data = []
        for slide in slides:
            slides_data.append({
                'slide_number': slide.slide_number,
                'text_content': slide.text_content,
                'image_base64': slide.image_base64
            })
        
        # Perform fact checking
        check_results = self.gemini_client.batch_check_facts(slides_data)
        
        # Process results
        report = self._generate_report(metadata, check_results)
        
        return report
    
    def _generate_report(self, metadata: Dict[str, Any], check_results: Dict[str, Any]) -> FactCheckReport:
        results = []
        slides_with_issues = 0
        total_issues = 0
        issues_by_type = {
            'date_error': 0,
            'numerical_error': 0,
            'technical_claim': 0,
            'citation_error': 0,
            'knowledge_consistency': 0
        }
        issues_by_severity = {
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        for result in check_results['results']:
            fact_result = FactCheckResult(
                slide_number=result.get('slide_number', 0),
                status=result.get('status', 'error'),
                issues=[],
                summary=result.get('summary', ''),
                token_usage=result.get('token_usage')
            )
            
            if result.get('status') == 'issues_found' and 'issues' in result:
                slides_with_issues += 1
                
                for issue in result['issues']:
                    fact_issue = FactIssue(
                        type=issue.get('type', 'unknown'),
                        severity=issue.get('severity', 'medium'),
                        original_text=issue.get('original_text', ''),
                        issue_description=issue.get('issue_description', ''),
                        correct_information=issue.get('correct_information'),
                        confidence=issue.get('confidence', 0.5),
                        slide_number=result['slide_number']
                    )
                    fact_result.issues.append(fact_issue)
                    total_issues += 1
                    
                    # Count by type and severity
                    if issue['type'] in issues_by_type:
                        issues_by_type[issue['type']] += 1
                    if issue['severity'] in issues_by_severity:
                        issues_by_severity[issue['severity']] += 1
            
            results.append(fact_result)
        
        return FactCheckReport(
            file_metadata=metadata,
            total_slides=len(check_results['results']),
            slides_with_issues=slides_with_issues,
            total_issues=total_issues,
            issues_by_type=issues_by_type,
            issues_by_severity=issues_by_severity,
            results=results,
            total_cost_estimate=check_results.get('total_cost_estimate', 0.0),
            timestamp=datetime.now().isoformat()
        )
    
    def quick_check(self, text: str) -> Dict[str, Any]:
        """Quick fact check for a single piece of text"""
        # Extract potential facts to check
        facts_to_check = []
        
        # Find dates
        dates = self.date_pattern.findall(text)
        for date in dates:
            context = self._extract_context(text, date)
            facts_to_check.append({
                'type': 'date',
                'value': date,
                'context': context
            })
        
        # Find numbers
        numbers = self.number_pattern.findall(text)
        for number in numbers:
            context = self._extract_context(text, number)
            facts_to_check.append({
                'type': 'number',
                'value': number,
                'context': context
            })
        
        # Check each fact
        verification_results = []
        for fact in facts_to_check[:5]:  # Limit to 5 facts for quick check
            result = self.gemini_client.verify_single_fact(fact['context'])
            verification_results.append(result)
        
        return {
            'text': text,
            'facts_found': len(facts_to_check),
            'facts_checked': len(verification_results),
            'verification_results': verification_results
        }
    
    def _extract_context(self, text: str, target: str, context_length: int = 100) -> str:
        """Extract context around a target string"""
        index = text.find(target)
        if index == -1:
            return target
        
        start = max(0, index - context_length)
        end = min(len(text), index + len(target) + context_length)
        
        context = text[start:end]
        if start > 0:
            context = '...' + context
        if end < len(text):
            context = context + '...'
        
        return context
    
    def export_report(self, report: FactCheckReport, format: str = 'json') -> str:
        """Export report in different formats"""
        if format == 'json':
            return report.model_dump_json(indent=2)
        
        elif format == 'html':
            return self._generate_html_report(report)
        
        elif format == 'markdown':
            return self._generate_markdown_report(report)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _generate_html_report(self, report: FactCheckReport) -> str:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ファクトチェックレポート - {report.file_metadata.get('file_name', 'Unknown')}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .issue {{ margin: 10px 0; padding: 10px; border-left: 3px solid #ff0000; }}
                .issue.high {{ border-color: #ff0000; }}
                .issue.medium {{ border-color: #ff9900; }}
                .issue.low {{ border-color: #ffcc00; }}
                .slide {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <h1>ファクトチェックレポート</h1>
            <div class="summary">
                <h2>サマリー</h2>
                <p>ファイル: {report.file_metadata.get('file_name', 'Unknown')}</p>
                <p>総スライド数: {report.total_slides}</p>
                <p>問題のあるスライド数: {report.slides_with_issues}</p>
                <p>総問題数: {report.total_issues}</p>
                <p>推定コスト: ${report.total_cost_estimate:.4f}</p>
            </div>
        """
        
        for result in report.results:
            if result.issues:
                html += f"""
                <div class="slide">
                    <h3>スライド {result.slide_number}</h3>
                    <p>{result.summary}</p>
                """
                
                for issue in result.issues:
                    html += f"""
                    <div class="issue {issue.severity}">
                        <strong>問題タイプ:</strong> {issue.type}<br>
                        <strong>深刻度:</strong> {issue.severity}<br>
                        <strong>該当テキスト:</strong> {issue.original_text}<br>
                        <strong>問題の説明:</strong> {issue.issue_description}<br>
                        """
                    if issue.correct_information:
                        html += f"<strong>正しい情報:</strong> {issue.correct_information}<br>"
                    html += f"<strong>信頼度:</strong> {issue.confidence:.2f}</div>"
                
                html += "</div>"
        
        html += "</body></html>"
        return html
    
    def _generate_markdown_report(self, report: FactCheckReport) -> str:
        md = f"""# ファクトチェックレポート

## ファイル情報
- ファイル名: {report.file_metadata.get('file_name', 'Unknown')}
- 作成日時: {report.timestamp}

## サマリー
- 総スライド数: {report.total_slides}
- 問題のあるスライド数: {report.slides_with_issues}
- 総問題数: {report.total_issues}
- 推定コスト: ${report.total_cost_estimate:.4f}

## 問題の種類別集計
"""
        
        for issue_type, count in report.issues_by_type.items():
            if count > 0:
                md += f"- {issue_type}: {count}件\n"
        
        md += "\n## 深刻度別集計\n"
        for severity, count in report.issues_by_severity.items():
            if count > 0:
                md += f"- {severity}: {count}件\n"
        
        md += "\n## 詳細結果\n"
        
        for result in report.results:
            if result.issues:
                md += f"\n### スライド {result.slide_number}\n"
                md += f"{result.summary}\n\n"
                
                for issue in result.issues:
                    md += f"#### 問題 ({issue.severity})\n"
                    md += f"- **タイプ**: {issue.type}\n"
                    md += f"- **該当テキスト**: {issue.original_text}\n"
                    md += f"- **説明**: {issue.issue_description}\n"
                    if issue.correct_information:
                        md += f"- **正しい情報**: {issue.correct_information}\n"
                    md += f"- **信頼度**: {issue.confidence:.2f}\n\n"
        
        return md