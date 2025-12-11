from flask import Flask, request, render_template, send_from_directory, jsonify
import os
from backend import process_excel

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        params = {
            'excel_filepath': filepath,
            'barcode_column_letter': request.form['barcode_col'],
            'start_row': int(request.form['start_row']),
            'end_row': int(request.form['end_row']),
            'image_column_letter': request.form['image_col'],
            'product_name_column_letter': request.form['name_col'],
            'translate_dst_column_letter': request.form['translate_col']
        }
        
        try:
            output_path = process_excel(**params)
            return jsonify({
                'success': True,
                'filename': os.path.basename(output_path)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5111, debug=False)
