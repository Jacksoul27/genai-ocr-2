import json
from flask import Flask, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv
import os
from PIL import Image
import cv2
import numpy as np
import re
import ssl

load_dotenv()

# Konfigurasi genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-pro")

# Inisialisasi Flask
app = Flask(__name__)

# Fungsi untuk mendeteksi fotokopi
def is_photocopy(image: Image.Image) -> bool:
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    total_pixels = image_cv.shape[0] * image_cv.shape[1]
    black_white_pixels = hist[0] + hist[255]
    proportion = black_white_pixels / total_pixels
    return proportion > 0.9

# Fungsi untuk memformat data yang diekstrak
def formatted_extract_data_ktp(data_ktp: str) -> dict:
    if not data_ktp.strip():
        return jsonify({
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find any KTP field in the uploaded picture",
            "data": None,
        }), 400

    lines = data_ktp.strip().split("\n")

    extracted_data = {
        "idNumber": None,
        "name": None,
        "bloodType": None,
        "religion": None,
        "gender": None,
        "birthPlaceBirthday": None,
        "province": None,
        "city": None,
        "district": None,
        "village": None,
        "rtrw": None,
        "occupation": None,
        "expiryDate": None,
        "nationality": None,
        "maritalStatus": None,
        "address": None,
        "placeOfBirth": None,
        "birthday": None,
    }

    birth_date_pattern = re.compile(r"(.+?)\s(\d{2}-\d{2}-\d{4})")

    for line in lines:
        if "NIK:" in line:
            extracted_data["idNumber"] = line.split(":")[1].strip()
        elif "Nama:" in line:
            extracted_data["name"] = line.split(":")[1].strip()
        elif "Golongan Darah:" in line:
            extracted_data["bloodType"] = line.split(":")[1].strip()
        elif "Agama:" in line:
            extracted_data["religion"] = line.split(":")[1].strip()
        elif "Jenis Kelamin:" in line:
            extracted_data["gender"] = line.split(":")[1].strip()
        elif "Tempat/Tgl.Lahir:" in line:
            birth_info = line.split(":")[1].strip()
            extracted_data["birthPlaceBirthday"] = birth_info

            # Jika tidak ada koma, gunakan regex
            if "," not in birth_info:
                match = birth_date_pattern.match(birth_info)
                if match:
                    extracted_data["placeOfBirth"] = match.group(1).strip()
                    extracted_data["birthday"] = match.group(2).strip().replace("-", "/")
            else:
                # Jika ada koma, pisahkan seperti biasa
                place, date = birth_info.split(",", 1)
                extracted_data["placeOfBirth"] = place.strip()
                extracted_data["birthday"] = date.strip().replace("-", "/")
        elif "Provinsi:" in line:
            extracted_data["province"] = line.split(":")[1].strip()
        elif "Kota/Kabupaten:" in line:
            extracted_data["city"] = line.split(":")[1].strip()
        elif "Kecamatan:" in line:
            extracted_data["district"] = line.split(":")[1].strip()
        elif "Kel/Desa:" in line:
            extracted_data["village"] = line.split(":")[1].strip()
        elif "RT/RW:" in line:
            extracted_data["rtrw"] = line.split(":")[1].strip()
        elif "Pekerjaan:" in line:
            extracted_data["occupation"] = line.split(":")[1].strip()
        elif "Berlaku Hingga:" in line:
            extracted_data["expiryDate"] = line.split(":")[1].strip()
        elif "Kewarganegaraan:" in line:
            extracted_data["nationality"] = line.split(":")[1].strip()
        elif "Status Perkawinan:" in line:
            extracted_data["maritalStatus"] = line.split(":")[1].strip()
        elif "Alamat:" in line:
            extracted_data["address"] = line.split(":")[1].strip()

    if all(value is None for value in extracted_data.values()):
        return jsonify ({
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find KTP field in uploaded picture",
            "data": None,
        }), 400
    
    return {
        "code": "SUCCESS",
        "message": "OK",
        "data": extracted_data,
    }

def format_extracted_data_faktur(data_faktur: str) -> dict:

    if not data_faktur.strip():
        return jsonify ({
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find Faktur field in uploaded picture",
            "data": None,
        }), 404
    
    lines = data_faktur.strip().split("\n")

    extracted_data_faktur = {
        "type": None,
        "jenis": None,
        "model": None,
        "tahun pembuatan": None,
        "isi silinder": None,
        "warna": None,
        "no. rangka/nik/vin": None,
        "no. mesin": None,
        "bahan bakar": None,
        "harga": None,
    }

    for line in lines:
        if "TYPE:" in line:
            extracted_data_faktur["type"] = line.split(":")[1].strip()
        elif "JENIS:" in line:
            extracted_data_faktur["jenis"] = line.split(":")[1].strip()
        elif "MODEL:" in line:
            extracted_data_faktur["model"] = line.split(":")[1].strip()
        elif "TAHUN PEMBUATAN:" in line:
            extracted_data_faktur["tahun pembuatan"] = line.split(":")[1].strip()
        elif "ISI SILINDER:" in line:
            extracted_data_faktur["isi silinder"] = line.split(":")[1].strip()
        elif "WARNA:" in line:
            extracted_data_faktur["warna"] = line.split(":")[1].strip()
        elif "NO. RANGKA/NIK/VIN:" in line:
            extracted_data_faktur["no. rangka/nik/vin"] = line.split(":")[1].strip()
        elif "NO. MESIN:" in line:
            extracted_data_faktur["no. mesin"] = line.split(":")[1].strip()
        elif "BAHAN BAKAR:" in line:
            extracted_data_faktur["bahan bakar"] = line.split(":")[1].strip()
        elif "HARGA:" in line:
            extracted_data_faktur["harga"] = line.split(":")[1].strip()

    if all(value is None for value in extracted_data_faktur.values()):
        return jsonify ({
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find any field in the uploaded picture",
            "data": None,
        }), 404
    
    response_faktur = {
        "code": "OCR_SUCCESS",
        "message": "OCR check success",
        "data": extracted_data_faktur,
    }

    return response_faktur

# Endpoint untuk ekstraksi data
@app.route("/extract-data-ktp", methods=["POST"])
def extract_data():
    if "file" not in request.files:
        return jsonify({
            "code": "NO_FILE",
            "message": "No file uploaded.",
            "data": None
        }), 400

    file = request.files["file"]
    valid_extensions = (".jpg", ".jpeg", ".png")
    valid_content_types = ("image/jpg", "image/jpeg", "image/png")

    if not file.filename.lower().endswith(valid_extensions) or file.mimetype not in valid_content_types:
        return jsonify({
            "code": "IMAGE_INVALID_FORMAT",
            "message": "Invalid image format. Use jpeg/jpg/png.",
            "data": None,
        }), 400

    try:
        image = Image.open(file)
        width, height = image.size
        if width < 256 or height < 256 or width > 4096 or height > 4096:
            return jsonify({
                "code": "IMAGE_INVALID_SIZE",
                "message": "Invalid image dimensions.",
                "data": None,
            }), 400

        if is_photocopy(image):
            return jsonify({
                "code": "IMAGE_IS_PHOTOCOPY",
                "message": "Image appears to be a photocopy.",
                "data": None,
            }), 400

        # Menggunakan model untuk ekstraksi konten
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
             """, image])
        
        extracted_data = formatted_extract_data_ktp(response.text)
        return jsonify(extracted_data)

    except Exception as e:
        return jsonify({
            "code": "SERVER_ERROR",
            "message": str(e),
            "data": None,
        }), 500
    
@app.route("/extract-data-faktur", methods=["POST"])
def extract_data_faktur():
    if "file" not in request.files:
        return jsonify({
            "code": "NO_FILE",
            "message": "No file uploaded.",
            "data": None,
        }), 400

    file_faktur = request.files["file"]
    valid_extensions = (".jpg", ".jpeg", ".png")
    valid_content_types = ("image/jpg", "image/jpeg", "image/png")

    if not file_faktur.filename.lower().endswith(valid_extensions) or file_faktur.mimetype not in valid_content_types:
        return jsonify({
            "code": "IMAGE_INVALID_FORMAT",
            "message": "Invalid image format. Use jpeg/jpg/png.",
            "data": None,
        }), 400

    try:
        image_faktur = Image.open(file_faktur)
        width, height = image_faktur.size
        if width < 256 or height < 256 or width > 4096 or height > 4096:
            return jsonify({
                "code": "IMAGE_INVALID_SIZE",
                "message": "Invalid image dimensions.",
                "data": None,
            }), 400

        if is_photocopy(image_faktur):
            return jsonify({
                "code": "IMAGE_IS_PHOTOCOPY",
                "message": "Image appears to be a photocopy.",
                "data": None,
            }), 400

        # Menggunakan model untuk ekstraksi konten
        response_faktur = model.generate_content(
            ["""Analisa dan Ekstrak semua informasi dalam faktur dengan format berikut: 
             TYPE:
             JENIS:
             MODEL:
             TAHUN PEMBUATAN:
             ISI SILINDER:
             WARNA:
             NO. RANGKA/NIK/VIN:
             NO. MESIN:
             BAHAN BAKAR:
             HARGA:

             jangan tambahkan apapun yang tidak perlu seperti simbol, tanda baca, dll. hanya tulisan saja. deteksi jika gambar hitam putih adalah fotokopi dan tidak bisa diproses.
             """, image_faktur])
        
        extracted_data_faktur = format_extracted_data_faktur(response_faktur.text)
        return jsonify(extracted_data_faktur)

    except Exception as e:
        return jsonify({
            "code": "SERVER_ERROR",
            "message": str(e),
            "data": None,
        }), 500

@app.route("/extract", methods=["POST"])
def extract_anythings():
    if "file" not in request.files:
        return jsonify({
            "code": "NO_FILE",
            "message": "No file uploaded.",
            "data": None,
        }), 400
    
    file_anything = request.files["file"]

    try:
        anything = Image.open(file_anything)

        # Menggunakan model untuk ekstraksi konten
        response_anything = model.generate_content(
            ["""
            Analisa dan Ekstrak semua informasi dalam file terlampir.
             """, anything])
        
        response_data_anything = {
            "code": "OK",
            "message": "Exraction Successful",
            "data": response_anything.to_dict()
        }

        return jsonify (response_data_anything), 200

    except Exception as e:
        return jsonify({
            "code": "SERVER_ERROR",
            "message": str(e),
            "data": None,
        }), 500


if __name__ == "__main__":
    cert_file = "./SSL/bundle.crt"
    key_file = "./SSL/csr.key"

    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    
    app.run(host='0.0.0.0', port=5000, ssl_context=context)
