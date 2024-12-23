from flask import Flask, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv
import os
from PIL import Image
import time
import io
import ssl
from io import BytesIO


load_dotenv()

# Konfigurasi genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# model = genai.GenerativeModel("gemini-1.5-pro")
# model = genai.GenerativeModel("gemini-1.5-flash")
model = genai.GenerativeModel("gemini-2.0-flash-exp")

# Inisialisasi Flask
app = Flask(__name__)


# Endpoint untuk ekstraksi data
@app.route("/extract-data-ktp", methods=["POST"])
def extract_data_ktp():
    if "file" not in request.files:
        return jsonify({
            "code": "NO_FILE",
            "message": "No file uploaded.",
            "data": None
        }), 400

    file_ktp = request.files["file"]
    print(f"Received file: {file_ktp.filename}, ContentType: {file_ktp.content_type}")
    valid_extensions = (".jpg", ".jpeg", ".png")
    # valid_content_types = ("image/jpg", "image/jpeg", "image/png")

    if not file_ktp.filename.lower().endswith(valid_extensions):
        return jsonify({
            "code": "IMAGE_INVALID_FORMAT",
            "message": "Invalid image format. Use jpeg/jpg/png.",
            "data": None,
        }), 400

    # image = Image.open(file)
    image_ktp = Image.open(file_ktp)


    response = model.generate_content(
        ["""Analisa dan Ekstrak semua informasi dalam KTP dengan format berikut: 
            NIK:
            Nama:
            Golongan Darah:
            Agama:
            Jenis Kelamin:
            Tempat/Tgl.Lahir:
            Provinsi:
            Kota/Kabupaten:
            Kecamatan:
            Kel/Desa:
            RT/RW:
            Pekerjaan:
            Berlaku Hingga:
            Kewarganegaraan:
            Status Perkawinan:
            Alamat:

            jangan tambahkan apapun yang tidak perlu seperti simbol, tanda baca, dll. hanya tulisan saja. deteksi jika gambar hitam putih adalah fotokopi dan tidak bisa diproses.
            """, image_ktp])
    print(response.text)
    
    return response.text

# Endpoint untuk ekstraksi data
@app.route("/extract-data-npwp", methods=["POST"])
def extract_data_npwp():
    if "file" not in request.files:
        return jsonify({
            "code": "NO_FILE",
            "message": "No file uploaded.",
            "data": None
        }), 400

    file_npwp = request.files["file"]
    print(f"Received file: {file_npwp.filename}, ContentType: {file_npwp.content_type}")
    valid_extensions = (".jpg", ".jpeg", ".png")
    # valid_content_types = ("image/jpg", "image/jpeg", "image/png")

    if not file_npwp.filename.lower().endswith(valid_extensions):
        return jsonify({
            "code": "IMAGE_INVALID_FORMAT",
            "message": "Invalid image format. Use jpeg/jpg/png.",
            "data": None,
        }), 400

    # image = Image.open(file)
    image_npwp = Image.open(file_npwp)


    response = model.generate_content(
        ["""Analisa dan Ekstrak semua informasi dalam KTP dengan format berikut: 
            NIK:
            Nama:
            Golongan Darah:
            Agama:
            Jenis Kelamin:
            Tempat/Tgl.Lahir:
            Provinsi:
            Kota/Kabupaten:
            Kecamatan:
            Kel/Desa:
            RT/RW:
            Pekerjaan:
            Berlaku Hingga:
            Kewarganegaraan:
            Status Perkawinan:
            Alamat:

            jangan tambahkan apapun yang tidak perlu seperti simbol, tanda baca, dll. hanya tulisan saja. deteksi jika gambar hitam putih adalah fotokopi dan tidak bisa diproses.
            """, image_npwp])
    print(response.text)
    
    return response.text



if __name__ == "__main__":
    cert_file = "./SSL/bundle.crt"
    key_file = "./SSL/csr.key"

    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    
    app.run(host='0.0.0.0', port=5050, ssl_context=context)
