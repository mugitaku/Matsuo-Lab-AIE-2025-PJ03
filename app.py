import os
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import json
from datetime import datetime

from src.core.fact_checker import FactChecker
from src.utils.report_generator import ReportGenerator

load_dotenv()

app = Flask(__name__, template_folder='src/web/templates', static_folder='src/web/static')
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['OUTPUT_FOLDER'] = './output'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'ppt', 'pptx', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath
        }), 200
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/check/<filename>', methods=['POST'])
def check_facts(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Initialize fact checker
        api_key = request.json.get('api_key') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400
        
        fact_checker = FactChecker(gemini_api_key=api_key)
        
        # Perform fact checking
        report = fact_checker.check_presentation(filepath)
        
        # Generate reports
        report_generator = ReportGenerator(app.config['OUTPUT_FOLDER'])
        saved_files = report_generator.save_report(report, os.path.splitext(filename)[0])
        
        # Generate improvement suggestions
        suggestions = report_generator.generate_improvement_suggestions(report)
        
        return jsonify({
            'success': True,
            'report': report.model_dump(),
            'saved_files': saved_files,
            'suggestions': suggestions
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/quick-check', methods=['POST'])
def quick_check():
    text = request.json.get('text', '')
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        api_key = request.json.get('api_key') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400
        
        fact_checker = FactChecker(gemini_api_key=api_key)
        result = fact_checker.quick_check(text)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<report_type>/<filename>')
def download_report(report_type, filename):
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filepath, as_attachment=True)

@app.route('/cost-estimate', methods=['POST'])
def estimate_cost():
    data = request.json
    slide_count = data.get('slide_count', 0)
    file_count = data.get('file_count', 1)
    
    # Rough estimation based on average tokens per slide
    avg_tokens_per_slide = 500  # Input tokens
    avg_output_tokens_per_slide = 200  # Output tokens
    
    input_price_per_1k = 0.00025
    output_price_per_1k = 0.0005
    
    total_input_tokens = slide_count * avg_tokens_per_slide * file_count
    total_output_tokens = slide_count * avg_output_tokens_per_slide * file_count
    
    input_cost = (total_input_tokens / 1000) * input_price_per_1k
    output_cost = (total_output_tokens / 1000) * output_price_per_1k
    total_cost = input_cost + output_cost
    
    return jsonify({
        'estimated_cost': round(total_cost, 4),
        'input_tokens': total_input_tokens,
        'output_tokens': total_output_tokens,
        'cost_breakdown': {
            'input_cost': round(input_cost, 4),
            'output_cost': round(output_cost, 4)
        }
    }), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)