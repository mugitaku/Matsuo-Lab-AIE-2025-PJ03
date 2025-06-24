#!/usr/bin/env python3
"""
テスト実行スクリプト

pytest を使用してテストスイートを実行します。
"""

import subprocess
import sys
import os

def run_tests():
    """テストを実行し、結果を表示"""
    print("=== 講義スライド ファクトチェッカー テストスイート ===")
    print()
    
    # pytestが利用可能かチェック
    try:
        subprocess.run(['pytest', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: pytest がインストールされていません")
        print("以下のコマンドでインストールしてください:")
        print("  pip install pytest")
        return 1
    
    # テストディレクトリの確認
    if not os.path.exists('tests'):
        print("Error: testsディレクトリが見つかりません")
        return 1
    
    # テストを実行
    print("テストを実行中...")
    print()
    
    try:
        # 詳細なテスト実行
        result = subprocess.run([
            'pytest', 
            'tests/',
            '-v',  # 詳細表示
            '--tb=short',  # エラー時の短いトレースバック
            '--durations=10',  # 実行時間の長いテスト上位10個を表示
            '--cov=src',  # カバレッジ計測（coverageがインストールされている場合）
            '--cov-report=term-missing'
        ], check=False)
        
        if result.returncode == 0:
            print("\n✅ すべてのテストが成功しました!")
            return 0
        else:
            print(f"\n❌ テストが失敗しました (終了コード: {result.returncode})")
            return result.returncode
            
    except FileNotFoundError:
        print("Error: pytest コマンドが見つかりません")
        return 1
    except Exception as e:
        print(f"Error: テスト実行中にエラーが発生しました: {e}")
        return 1

def run_specific_test(test_file):
    """特定のテストファイルを実行"""
    if not os.path.exists(f'tests/{test_file}'):
        print(f"Error: tests/{test_file} が見つかりません")
        return 1
    
    print(f"=== {test_file} を実行中 ===")
    
    try:
        result = subprocess.run([
            'pytest', 
            f'tests/{test_file}',
            '-v',
            '--tb=short'
        ], check=False)
        
        return result.returncode
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        # 特定のテストファイルを実行
        test_file = sys.argv[1]
        if not test_file.startswith('test_'):
            test_file = f'test_{test_file}'
        if not test_file.endswith('.py'):
            test_file = f'{test_file}.py'
        
        return run_specific_test(test_file)
    else:
        # すべてのテストを実行
        return run_tests()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)