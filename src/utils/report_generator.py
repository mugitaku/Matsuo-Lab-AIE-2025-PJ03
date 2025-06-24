import os
from datetime import datetime
from typing import Dict, Any, List
import json
from src.core.fact_checker import FactCheckReport


class ReportGenerator:
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def save_report(self, report: FactCheckReport, base_filename: str) -> Dict[str, str]:
        """Save report in multiple formats and return file paths"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{base_filename}_{timestamp}"
        
        saved_files = {}
        
        # Save JSON
        json_path = os.path.join(self.output_dir, f"{base_name}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(report.model_dump_json(indent=2, ensure_ascii=False))
        saved_files['json'] = json_path
        
        # Save HTML
        from src.core.fact_checker import FactChecker
        checker = FactChecker()
        html_content = checker.export_report(report, 'html')
        html_path = os.path.join(self.output_dir, f"{base_name}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        saved_files['html'] = html_path
        
        # Save Markdown
        md_content = checker.export_report(report, 'markdown')
        md_path = os.path.join(self.output_dir, f"{base_name}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        saved_files['markdown'] = md_path
        
        return saved_files
    
    def generate_summary_dashboard(self, reports: List[FactCheckReport]) -> str:
        """Generate a summary dashboard for multiple reports"""
        dashboard_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ファクトチェック ダッシュボード</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .report-card { 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 5px;
                }
                .stats { 
                    display: flex; 
                    justify-content: space-around; 
                    margin: 10px 0;
                }
                .stat-item { 
                    text-align: center; 
                    padding: 10px;
                }
                .stat-value { 
                    font-size: 24px; 
                    font-weight: bold; 
                    color: #333;
                }
                .issue-high { color: #ff0000; }
                .issue-medium { color: #ff9900; }
                .issue-low { color: #ffcc00; }
            </style>
        </head>
        <body>
            <h1>ファクトチェック ダッシュボード</h1>
            <p>生成日時: {timestamp}</p>
            
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value">{total_files}</div>
                    <div>チェック済みファイル</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{total_slides}</div>
                    <div>総スライド数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{total_issues}</div>
                    <div>検出された問題</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${total_cost:.4f}</div>
                    <div>総コスト</div>
                </div>
            </div>
            
            <h2>ファイル別結果</h2>
        """.format(
            timestamp=datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),
            total_files=len(reports),
            total_slides=sum(r.total_slides for r in reports),
            total_issues=sum(r.total_issues for r in reports),
            total_cost=sum(r.total_cost_estimate for r in reports)
        )
        
        for report in reports:
            high_issues = report.issues_by_severity.get('high', 0)
            medium_issues = report.issues_by_severity.get('medium', 0)
            low_issues = report.issues_by_severity.get('low', 0)
            
            dashboard_html += f"""
            <div class="report-card">
                <h3>{report.file_metadata.get('file_name', 'Unknown')}</h3>
                <p>スライド数: {report.total_slides} | 問題のあるスライド: {report.slides_with_issues}</p>
                <p>
                    問題数: 
                    <span class="issue-high">高: {high_issues}</span> | 
                    <span class="issue-medium">中: {medium_issues}</span> | 
                    <span class="issue-low">低: {low_issues}</span>
                </p>
                <p>推定コスト: ${report.total_cost_estimate:.4f}</p>
            </div>
            """
        
        dashboard_html += """
        </body>
        </html>
        """
        
        dashboard_path = os.path.join(self.output_dir, f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
        
        return dashboard_path
    
    def generate_improvement_suggestions(self, report: FactCheckReport) -> Dict[str, Any]:
        """Generate suggestions for improving the slides based on fact-check results"""
        suggestions = {
            'slide_suggestions': {},
            'general_recommendations': [],
            'priority_fixes': []
        }
        
        # Analyze issues by type
        if report.issues_by_type['date_error'] > 0:
            suggestions['general_recommendations'].append(
                "日付や年代の確認を徹底してください。特に技術の発明年や論文の発表年に注意。"
            )
        
        if report.issues_by_type['numerical_error'] > 0:
            suggestions['general_recommendations'].append(
                "数値データ（パラメータ数、ベンチマークスコアなど）の最新情報を確認してください。"
            )
        
        if report.issues_by_type['citation_error'] > 0:
            suggestions['general_recommendations'].append(
                "引用・参照情報を正確に記載し、出典を明記してください。"
            )
        
        # Generate slide-specific suggestions
        for result in report.results:
            if result.issues:
                slide_suggestions = []
                
                # Sort issues by severity
                high_priority_issues = [i for i in result.issues if i.severity == 'high']
                medium_priority_issues = [i for i in result.issues if i.severity == 'medium']
                
                if high_priority_issues:
                    for issue in high_priority_issues:
                        suggestion = {
                            'issue': issue.original_text,
                            'correction': issue.correct_information or "要確認",
                            'action': f"修正必須: {issue.issue_description}"
                        }
                        slide_suggestions.append(suggestion)
                        suggestions['priority_fixes'].append({
                            'slide': result.slide_number,
                            'issue': issue.original_text,
                            'severity': 'high'
                        })
                
                if medium_priority_issues:
                    for issue in medium_priority_issues:
                        suggestion = {
                            'issue': issue.original_text,
                            'correction': issue.correct_information or "要確認",
                            'action': f"確認推奨: {issue.issue_description}"
                        }
                        slide_suggestions.append(suggestion)
                
                suggestions['slide_suggestions'][f'slide_{result.slide_number}'] = slide_suggestions
        
        return suggestions
    
    def export_cost_analysis(self, reports: List[FactCheckReport]) -> str:
        """Export cost analysis for multiple reports"""
        analysis = {
            'total_cost': sum(r.total_cost_estimate for r in reports),
            'average_cost_per_file': sum(r.total_cost_estimate for r in reports) / len(reports) if reports else 0,
            'average_cost_per_slide': sum(r.total_cost_estimate for r in reports) / sum(r.total_slides for r in reports) if reports else 0,
            'file_costs': []
        }
        
        for report in reports:
            file_cost = {
                'filename': report.file_metadata.get('file_name', 'Unknown'),
                'slides': report.total_slides,
                'cost': report.total_cost_estimate,
                'cost_per_slide': report.total_cost_estimate / report.total_slides if report.total_slides > 0 else 0
            }
            analysis['file_costs'].append(file_cost)
        
        # Generate cost projection
        analysis['projection'] = {
            '10_files': analysis['average_cost_per_file'] * 10,
            '100_files': analysis['average_cost_per_file'] * 100,
            '1000_files': analysis['average_cost_per_file'] * 1000,
            '100_slides': analysis['average_cost_per_slide'] * 100,
            '1000_slides': analysis['average_cost_per_slide'] * 1000,
            '10000_slides': analysis['average_cost_per_slide'] * 10000
        }
        
        cost_path = os.path.join(self.output_dir, f"cost_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(cost_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        return cost_path