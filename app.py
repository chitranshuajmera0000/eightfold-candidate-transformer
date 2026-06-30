import os
import json
import subprocess
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import tempfile
import shutil

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process_data():
    # Create a temporary directory for this request
    temp_dir = tempfile.mkdtemp()
    notes_dir = os.path.join(temp_dir, 'notes')
    os.makedirs(notes_dir)
    
    cmd_args = ['python', 'main.py']
    
    try:
        # Handle CSV
        if 'csv_file' in request.files and request.files['csv_file'].filename:
            f = request.files['csv_file']
            path = os.path.join(temp_dir, secure_filename(f.filename))
            f.save(path)
            cmd_args.extend(['--csv', path])
            
        # Handle ATS JSON
        if 'ats_file' in request.files and request.files['ats_file'].filename:
            f = request.files['ats_file']
            path = os.path.join(temp_dir, secure_filename(f.filename))
            f.save(path)
            cmd_args.extend(['--ats-json', path])
            
        # Handle LinkedIn JSON
        if 'linkedin_file' in request.files and request.files['linkedin_file'].filename:
            f = request.files['linkedin_file']
            path = os.path.join(temp_dir, secure_filename(f.filename))
            f.save(path)
            cmd_args.extend(['--linkedin-json', path])
            
        # Handle GitHub JSON
        if 'github_file' in request.files and request.files['github_file'].filename:
            f = request.files['github_file']
            path = os.path.join(temp_dir, secure_filename(f.filename))
            f.save(path)
            cmd_args.extend(['--github-json', path])
            
        # Handle Notes (multiple files)
        notes_files = request.files.getlist('notes_files')
        has_notes = False
        for f in notes_files:
            if f.filename:
                path = os.path.join(notes_dir, secure_filename(f.filename))
                f.save(path)
                has_notes = True
        if has_notes:
            cmd_args.extend(['--notes', notes_dir])
            
        # Handle Config JSON
        if 'config_file' in request.files and request.files['config_file'].filename:
            f = request.files['config_file']
            path = os.path.join(temp_dir, secure_filename(f.filename))
            f.save(path)
            cmd_args.extend(['--config', path])
            
        # Output file
        out_path = os.path.join(temp_dir, 'output.json')
        cmd_args.extend(['--out', out_path])
        
        # Run pipeline
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        
        if not os.path.exists(out_path):
            return jsonify({"error": "Pipeline failed to produce output", "logs": result.stderr}), 500
            
        with open(out_path, 'r', encoding='utf-8') as f:
            final_data = json.load(f)
            
        return jsonify({
            "success": True,
            "data": final_data,
            "logs": result.stdout + "\n" + result.stderr
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
