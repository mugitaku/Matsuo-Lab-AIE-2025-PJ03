#!/usr/bin/env python3
"""
講義スライド ファクトチェッカー 使用例

このスクリプトは、ファクトチェッカーの基本的な使用方法を示します。
"""

import os
from dotenv import load_dotenv
from src.core.fact_checker import FactChecker
from src.utils.report_generator import ReportGenerator
from src.utils.cost_estimator import CostEstimator

# 環境変数を読み込み
load_dotenv()

def main():
    # Google Gemini APIキーを設定
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: GOOGLE_API_KEY環境変数が設定されていません")
        print("1. .env.exampleをコピーして.envファイルを作成")
        print("2. Google AI StudioからAPIキーを取得: https://makersuite.google.com/app/apikey")
        print("3. .envファイルにAPIキーを設定")
        return
    
    # ファクトチェッカーを初期化
    fact_checker = FactChecker(gemini_api_key=api_key)
    
    # サンプルファイルのパス（実際のファイルパスに置換してください）
    sample_files = [
        "./LLM2024/01_Overview.pptx",
        "./LLM2024/03_Pre-training.pptx"
    ]
    
    print("=== 講義スライド ファクトチェッカー ===")
    print()
    
    # 1. コスト試算の例
    print("1. コスト試算")
    cost_estimator = CostEstimator()
    
    # 単一ファイルの試算
    single_file_estimate = cost_estimator.estimate_single_file(
        slide_count=25,  # 平均的なスライド数
        has_images=True
    )
    print(f"25スライドのファイル1つの推定コスト: ${single_file_estimate['cost_breakdown']['total_cost']:.4f}")
    
    # バッチ処理の試算
    batch_estimate = cost_estimator.estimate_batch([
        {'filename': 'file1.pptx', 'slide_count': 25, 'has_images': True},
        {'filename': 'file2.pptx', 'slide_count': 30, 'has_images': True},
        {'filename': 'file3.pdf', 'slide_count': 20, 'has_images': False}
    ])
    print(f"3ファイル一括処理の推定コスト: ${batch_estimate['total_cost']:.4f}")
    print()
    
    # 2. クイックチェックの例
    print("2. クイックチェック機能")
    sample_text = """
    Transformerモデルは2015年に発明され、自然言語処理の分野を革新しました。
    GPT-3は200Bのパラメータを持ち、ChatGPTは2021年にリリースされました。
    これらのモデルは人工知能の進歩において重要な役割を果たしています。
    """
    
    try:
        quick_result = fact_checker.quick_check(sample_text)
        print(f"検出されたファクト: {quick_result['facts_found']}件")
        print(f"チェック済み: {quick_result['facts_checked']}件")
        
        for i, verification in enumerate(quick_result.get('verification_results', []), 1):
            if not verification.get('parse_error'):
                print(f"  {i}. {verification.get('fact_text', 'N/A')}")
                print(f"     正確性: {'✓' if verification.get('is_correct') else '✗'}")
                print(f"     信頼度: {verification.get('confidence', 0):.2f}")
        print()
    except Exception as e:
        print(f"クイックチェック中にエラーが発生: {e}")
        print()
    
    # 3. ファイル処理の例（実際のファイルが存在する場合）
    print("3. ファイル処理")
    for file_path in sample_files:
        if os.path.exists(file_path):
            print(f"ファイルを処理中: {file_path}")
            try:
                # ファクトチェック実行
                report = fact_checker.check_presentation(file_path)
                
                print(f"  - 総スライド数: {report.total_slides}")
                print(f"  - 問題のあるスライド: {report.slides_with_issues}")
                print(f"  - 検出された問題: {report.total_issues}")
                print(f"  - 推定コスト: ${report.total_cost_estimate:.4f}")
                
                # レポート生成
                report_generator = ReportGenerator()
                base_filename = os.path.splitext(os.path.basename(file_path))[0]
                saved_files = report_generator.save_report(report, base_filename)
                
                print("  - 生成されたレポート:")
                for format_type, file_path in saved_files.items():
                    print(f"    {format_type.upper()}: {file_path}")
                
                # 改善提案
                suggestions = report_generator.generate_improvement_suggestions(report)
                if suggestions['priority_fixes']:
                    print(f"  - 優先修正項目: {len(suggestions['priority_fixes'])}件")
                
                print()
                
            except Exception as e:
                print(f"  エラー: {e}")
                print()
        else:
            print(f"ファイルが見つかりません: {file_path}")
    
    # 4. 使用方法の案内
    print("4. Webアプリケーション")
    print("より簡単に使用するには、Webアプリケーションを起動してください:")
    print("  python app.py")
    print("  ブラウザで http://localhost:5000 にアクセス")
    print()
    
    print("=== 完了 ===")


if __name__ == "__main__":
    main()