import os
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import shutil
import subprocess

UPLOAD_FOLDER = 'newdocs'
DOCS_FOLDER = 'docs'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

file_api = Blueprint('file_api', __name__)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@file_api.route('/api/docs/process_new', methods=['POST'])
def process_new_docs():
    # 1. base.py ile new_data.json oluştur
    base_result = subprocess.run(['python', 'base.py', '--input', UPLOAD_FOLDER, '--output', 'new_data.json'], capture_output=True, text=True)
    if base_result.returncode != 0:
        return jsonify({'error': 'base.py failed', 'details': base_result.stderr}), 500
    # 2. embedder.py ile new_data_with_embeddings.json oluştur
    embed_result = subprocess.run(['python', 'embedder.py', '--input', 'new_data.json', '--output', 'new_data_with_embeddings.json'], capture_output=True, text=True)
    if embed_result.returncode != 0:
        return jsonify({'error': 'embedder.py failed', 'details': embed_result.stderr}), 500
    # 3. chroma.py ile chroma'ya ekle
    chroma_result = subprocess.run(['python', 'chroma.py', '--input', 'new_data_with_embeddings.json'], capture_output=True, text=True)
    if chroma_result.returncode != 0:
        return jsonify({'error': 'chroma.py failed', 'details': chroma_result.stderr}), 500
    # 4. newdocs içindekileri docs'a taşı
    for fname in os.listdir(UPLOAD_FOLDER):
        shutil.move(os.path.join(UPLOAD_FOLDER, fname), os.path.join(DOCS_FOLDER, fname))
    # 5. new jsonları ana jsonlara ekle/taşı (örnek: eduroam_data.json)
    # Burada birleştirme veya taşıma işlemi yapılabilir, örnek olarak taşıyalım:
    shutil.move('new_data.json', 'eduroam_data.json')
    shutil.move('new_data_with_embeddings.json', 'eduroam_data_with_embeddings.json')
    # 6. newdocs klasörünü temizle
    for fname in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, fname))
    return jsonify({'success': True})
