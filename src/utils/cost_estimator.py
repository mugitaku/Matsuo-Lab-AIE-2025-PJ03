from typing import Dict, Any, List
import json


class CostEstimator:
    def __init__(self):
        # Gemini Pro pricing (as of 2024)
        self.pricing = {
            'gemini_pro': {
                'input_per_1k_tokens': 0.00025,
                'output_per_1k_tokens': 0.0005
            },
            'gemini_pro_vision': {
                'input_per_1k_tokens': 0.00025,
                'output_per_1k_tokens': 0.0005,
                'image_per_image': 0.0025  # Approximate cost per image
            }
        }
        
        # Average token estimates per slide
        self.avg_tokens_per_slide = {
            'text_only': {
                'input': 300,   # Text content + prompt
                'output': 150   # Fact check results
            },
            'with_image': {
                'input': 500,   # Text + image description + prompt
                'output': 200   # More detailed results
            }
        }
    
    def estimate_single_file(self, slide_count: int, has_images: bool = True) -> Dict[str, Any]:
        """Estimate cost for a single file"""
        if has_images:
            tokens = self.avg_tokens_per_slide['with_image']
            model_pricing = self.pricing['gemini_pro_vision']
            image_cost = slide_count * model_pricing.get('image_per_image', 0)
        else:
            tokens = self.avg_tokens_per_slide['text_only']
            model_pricing = self.pricing['gemini_pro']
            image_cost = 0
        
        total_input_tokens = slide_count * tokens['input']
        total_output_tokens = slide_count * tokens['output']
        
        input_cost = (total_input_tokens / 1000) * model_pricing['input_per_1k_tokens']
        output_cost = (total_output_tokens / 1000) * model_pricing['output_per_1k_tokens']
        
        total_cost = input_cost + output_cost + image_cost
        
        return {
            'slide_count': slide_count,
            'has_images': has_images,
            'tokens': {
                'input': total_input_tokens,
                'output': total_output_tokens,
                'total': total_input_tokens + total_output_tokens
            },
            'cost_breakdown': {
                'input_cost': round(input_cost, 6),
                'output_cost': round(output_cost, 6),
                'image_cost': round(image_cost, 6),
                'total_cost': round(total_cost, 6)
            },
            'cost_per_slide': round(total_cost / slide_count, 6) if slide_count > 0 else 0
        }
    
    def estimate_batch(self, files_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate cost for multiple files"""
        total_slides = 0
        total_cost = 0
        total_input_tokens = 0
        total_output_tokens = 0
        file_estimates = []
        
        for file_info in files_info:
            estimate = self.estimate_single_file(
                file_info.get('slide_count', 20),
                file_info.get('has_images', True)
            )
            file_estimates.append({
                'filename': file_info.get('filename', 'Unknown'),
                'estimate': estimate
            })
            
            total_slides += estimate['slide_count']
            total_cost += estimate['cost_breakdown']['total_cost']
            total_input_tokens += estimate['tokens']['input']
            total_output_tokens += estimate['tokens']['output']
        
        return {
            'file_count': len(files_info),
            'total_slides': total_slides,
            'total_tokens': {
                'input': total_input_tokens,
                'output': total_output_tokens,
                'total': total_input_tokens + total_output_tokens
            },
            'total_cost': round(total_cost, 4),
            'average_cost_per_file': round(total_cost / len(files_info), 4) if files_info else 0,
            'average_cost_per_slide': round(total_cost / total_slides, 6) if total_slides > 0 else 0,
            'file_estimates': file_estimates
        }
    
    def project_costs(self, base_estimate: Dict[str, Any]) -> Dict[str, Any]:
        """Project costs for larger volumes"""
        avg_cost_per_file = base_estimate.get('average_cost_per_file', 0)
        avg_cost_per_slide = base_estimate.get('average_cost_per_slide', 0)
        
        projections = {
            'by_files': {
                '10_files': round(avg_cost_per_file * 10, 2),
                '50_files': round(avg_cost_per_file * 50, 2),
                '100_files': round(avg_cost_per_file * 100, 2),
                '500_files': round(avg_cost_per_file * 500, 2),
                '1000_files': round(avg_cost_per_file * 1000, 2)
            },
            'by_slides': {
                '100_slides': round(avg_cost_per_slide * 100, 2),
                '500_slides': round(avg_cost_per_slide * 500, 2),
                '1000_slides': round(avg_cost_per_slide * 1000, 2),
                '5000_slides': round(avg_cost_per_slide * 5000, 2),
                '10000_slides': round(avg_cost_per_slide * 10000, 2)
            },
            'monthly_estimates': {
                'light_usage': {
                    'description': '10 files/month (200 slides)',
                    'cost': round(avg_cost_per_file * 10, 2)
                },
                'moderate_usage': {
                    'description': '50 files/month (1000 slides)',
                    'cost': round(avg_cost_per_file * 50, 2)
                },
                'heavy_usage': {
                    'description': '200 files/month (4000 slides)',
                    'cost': round(avg_cost_per_file * 200, 2)
                },
                'enterprise_usage': {
                    'description': '1000 files/month (20000 slides)',
                    'cost': round(avg_cost_per_file * 1000, 2)
                }
            }
        }
        
        return projections
    
    def generate_cost_report(self, actual_usage: List[Dict[str, Any]]) -> str:
        """Generate a detailed cost report based on actual usage"""
        total_cost = sum(item.get('cost', 0) for item in actual_usage)
        total_slides = sum(item.get('slides', 0) for item in actual_usage)
        
        report = f"""
# ファクトチェック コスト分析レポート

## 実績サマリー
- 処理ファイル数: {len(actual_usage)}
- 総スライド数: {total_slides}
- 総コスト: ${total_cost:.4f}
- 平均コスト/ファイル: ${total_cost/len(actual_usage):.4f}
- 平均コスト/スライド: ${total_cost/total_slides:.6f}

## コスト内訳
"""
        
        # Group by date if available
        by_date = {}
        for item in actual_usage:
            date = item.get('date', 'Unknown')
            if date not in by_date:
                by_date[date] = {'files': 0, 'slides': 0, 'cost': 0}
            by_date[date]['files'] += 1
            by_date[date]['slides'] += item.get('slides', 0)
            by_date[date]['cost'] += item.get('cost', 0)
        
        for date, stats in sorted(by_date.items()):
            report += f"\n### {date}\n"
            report += f"- ファイル数: {stats['files']}\n"
            report += f"- スライド数: {stats['slides']}\n"
            report += f"- コスト: ${stats['cost']:.4f}\n"
        
        # Add projections
        base_estimate = {
            'average_cost_per_file': total_cost / len(actual_usage) if actual_usage else 0,
            'average_cost_per_slide': total_cost / total_slides if total_slides > 0 else 0
        }
        projections = self.project_costs(base_estimate)
        
        report += "\n## 将来のコスト予測\n"
        report += "\n### ファイル数別\n"
        for volume, cost in projections['by_files'].items():
            report += f"- {volume}: ${cost:.2f}\n"
        
        report += "\n### 月次利用予測\n"
        for usage_type, info in projections['monthly_estimates'].items():
            report += f"- {usage_type}: {info['description']} - ${info['cost']:.2f}/月\n"
        
        return report
    
    def save_cost_analysis(self, analysis: Dict[str, Any], filename: str):
        """Save cost analysis to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)