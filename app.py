from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory
from flask_cors import CORS
from uuid import uuid4
from blockchain import Blockchain
import os
import hashlib

app = Flask(__name__)
CORS(app)

# ID unik node
node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()

# Folder upload
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    chain = blockchain.chain
    length = len(chain)
    return render_template('index.html', chain=chain, length=length)

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block['proof'])

    # Tambahkan transaksi dummy
    blockchain.new_transaction(
        id_tanah=None,
        pemilik_lama=None,
        pemilik_baru=node_identifier,
        lokasi="Server",
        file_hash=None,
        file_url=None
    )

    block = blockchain.new_block(proof)
    response = {
        'message': "Blok baru telah ditambang (Proof of Work)",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
        'consensus': block['consensus']
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json(silent=True) or {}

    if not values:
        values = {
            'id_tanah': request.form.get('id_tanah'),
            'pemilik_lama': request.form.get('pemilik_lama'),
            'pemilik_baru': request.form.get('pemilik_baru'),
            'lokasi': request.form.get('lokasi'),
            'file_hash': None,
            'file_url': None
        }

        file = request.files.get('file')
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            with open(filepath, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            values['file_hash'] = file_hash
            values['file_url'] = f"/uploads/{file.filename}"

    required = ['id_tanah', 'pemilik_lama', 'pemilik_baru', 'lokasi']
    if not all(k in values and values[k] for k in required):
        return render_template('index.html', chain=blockchain.chain, error="❌ Data belum lengkap!")

    blockchain.new_transaction(
        values['id_tanah'],
        values['pemilik_lama'],
        values['pemilik_baru'],
        values['lokasi'],
        values.get('file_hash'),
        values.get('file_url')
    )

    # Tambang otomatis blok baru agar langsung muncul
    proof = blockchain.proof_of_work(blockchain.last_block['proof'])
    blockchain.new_block(proof)

    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {'chain': blockchain.chain, 'length': len(blockchain.chain)}
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json(silent=True) or {}
    nodes = values.get('nodes')
    if not nodes:
        return jsonify({'error': 'Silakan berikan daftar node'}), 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'Node baru telah terdaftar',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {'message': 'Rantai telah diganti', 'new_chain': blockchain.chain}
    else:
        response = {'message': 'Rantai sudah paling valid', 'chain': blockchain.chain}
    return jsonify(response), 200

if __name__ == '__main__':
    import sys
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True)
