import os
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import json
import base64
from PIL import Image
import io

load_dotenv()


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key is required")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.vision_model = genai.GenerativeModel('gemini-pro-vision')
        
        # Token pricing for cost estimation
        self.input_price_per_1k = 0.00025
        self.output_price_per_1k = 0.0005
    
    def check_facts(self, content: str, slide_number: int, image_base64: Optional[str] = None) -> Dict[str, Any]:
        prompt = self._create_fact_check_prompt(content, slide_number)
        
        try:
            if image_base64:
                # Use vision model for slides with images
                image_data = base64.b64decode(image_base64)
                image = Image.open(io.BytesIO(image_data))
                response = self.vision_model.generate_content([prompt, image])
            else:
                # Use text model for text-only slides
                response = self.model.generate_content(prompt)
            
            # Parse the response
            result = self._parse_fact_check_response(response.text, slide_number)
            
            # Estimate tokens used (rough estimation)
            input_tokens = len(prompt.split()) * 1.3  # Rough token estimation
            output_tokens = len(response.text.split()) * 1.3
            
            result['token_usage'] = {
                'input_tokens': int(input_tokens),
                'output_tokens': int(output_tokens),
                'estimated_cost': self._calculate_cost(input_tokens, output_tokens)
            }
            
            return result
            
        except Exception as e:
            return {
                'slide_number': slide_number,
                'status': 'error',
                'error_message': str(e),
                'issues': []
            }
    
    def _create_fact_check_prompt(self, content: str, slide_number: int) -> str:
        return f"""
        あなたは講義スライドのファクトチェックを行う専門家です。
        以下のスライド{slide_number}の内容について、事実確認を行ってください。
        
        確認すべき項目：
        1. 年代・日付の正確性（例：「Transformerは2017年に発明された」など）
        2. 数値データの正確性（モデルのパラメータ数、ベンチマークスコアなど）
        3. 技術的な主張の妥当性
        4. 引用・参照情報の正確性
        5. 一般的な知識との整合性
        
        スライドの内容：
        {content}
        
        以下の形式でJSON形式で回答してください：
        {{
            "slide_number": {slide_number},
            "status": "ok" または "issues_found",
            "issues": [
                {{
                    "type": "date_error" | "numerical_error" | "technical_claim" | "citation_error" | "knowledge_consistency",
                    "severity": "high" | "medium" | "low",
                    "original_text": "問題のあるテキスト",
                    "issue_description": "問題の説明",
                    "correct_information": "正しい情報（分かる場合）",
                    "confidence": 0.0-1.0
                }}
            ],
            "summary": "全体的な評価のサマリー"
        }}
        
        問題が見つからない場合は、issuesを空の配列[]として返してください。
        """
    
    def _parse_fact_check_response(self, response_text: str, slide_number: int) -> Dict[str, Any]:
        try:
            # Extract JSON from the response
            # Sometimes the model returns markdown code blocks
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text.strip()
            
            result = json.loads(json_text)
            return result
            
        except json.JSONDecodeError:
            # Fallback: Try to extract meaningful information
            return {
                'slide_number': slide_number,
                'status': 'parse_error',
                'raw_response': response_text,
                'issues': [],
                'summary': 'Response parsing failed'
            }
    
    def _calculate_cost(self, input_tokens: float, output_tokens: float) -> float:
        input_cost = (input_tokens / 1000) * self.input_price_per_1k
        output_cost = (output_tokens / 1000) * self.output_price_per_1k
        return round(input_cost + output_cost, 6)
    
    def batch_check_facts(self, slides_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        total_cost = 0.0
        
        for slide in slides_content:
            result = self.check_facts(
                slide.get('text_content', ''),
                slide.get('slide_number', 0),
                slide.get('image_base64', None)
            )
            results.append(result)
            
            if 'token_usage' in result:
                total_cost += result['token_usage']['estimated_cost']
        
        return {
            'results': results,
            'total_cost_estimate': round(total_cost, 4),
            'slides_checked': len(slides_content)
        }
    
    def verify_single_fact(self, fact_text: str) -> Dict[str, Any]:
        prompt = f"""
        以下の文章が事実として正しいか検証してください：
        "{fact_text}"
        
        回答は以下の形式のJSONで返してください：
        {{
            "fact_text": "{fact_text}",
            "is_correct": true/false,
            "confidence": 0.0-1.0,
            "explanation": "説明",
            "correct_information": "正しい情報（該当する場合）",
            "sources": ["参考になる情報源のリスト"]
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            return self._parse_verification_response(response.text)
        except Exception as e:
            return {
                'fact_text': fact_text,
                'is_correct': None,
                'error': str(e)
            }
    
    def _parse_verification_response(self, response_text: str) -> Dict[str, Any]:
        try:
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text.strip()
            
            return json.loads(json_text)
        except:
            return {'parse_error': True, 'raw_response': response_text}