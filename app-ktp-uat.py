import json
from operator import contains
from flask import Flask, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv
import os
from PIL import Image
import cv2
import numpy as np
import re
import ssl
import pyodbc
import pytesseract
from datetime import datetime


load_dotenv()

DB_DRIVER = os.getenv("DB_DRIVER")
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Konfigurasi genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-pro")

# Inisialisasi Flask
app = Flask(__name__)

# Fungsi untuk mendeteksi fotokopi
def is_photocopy(image: Image.Image) -> bool:
    # Konversi objek PIL.Image ke array numpy
    imagecv = np.array(image)

    # Pastikan format gambar dalam BGR jika menggunakan OpenCV
    if imagecv.ndim == 2:  # Jika grayscale, tambahkan dimensi untuk channel
        imagecv = cv2.cvtColor(imagecv, cv2.COLOR_GRAY2BGR)

    # Convert gambar ke grayscale
    grayscale = cv2.cvtColor(imagecv, cv2.COLOR_BGR2GRAY)
    
    # Melakukan thresholding untuk memisahkan elemen-elemen yang berbeda
    _, thresholded = cv2.threshold(grayscale, 240, 255, cv2.THRESH_BINARY)
    
    # Menghitung jumlah kontur
    contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Jika jumlah kontur melebihi nilai tertentu, gambar kemungkinan besar adalah fotokopi
    print(f"Jumlah kontur: {len(contours)}")
    if len(contours) > 2500:  
        return True
    else:
        return False

# Fungsi untuk menyimpan ke database
def save_to_mssql_ktp(data):
    connection_string = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
    )

    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query = """
        EXEC SaveToOCRKTP ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        """
        cursor.execute(query, (
            data["idNumber"], data["name"], data["bloodType"], data["religion"], 
            data["gender"], data["birthPlaceBirthday"], data["province"], data["city"], 
            data["district"], data["village"], data["rtrw"], data["occupation"], 
            data["expiryDate"], data["nationality"], data["maritalStatus"], data["address"], 
            data["placeOfBirth"], data["birthday"]
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

# Fungsi untuk menyimpan ke database
def save_to_mssql_faktur(data):
    connection_string = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
    )

    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query = """
        EXEC SaveToOCRFAKTUR ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        """
        cursor.execute(query, (
            data["type"], data["jenis"], data["model"], data["tahun pembuatan"],
            data["isi silinder"], data["warna"], data["no. rangka/nik/vin"], data["no. mesin"], 
            data["bahan bakar"], data["harga"]
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

# Fungsi untuk menyimpan ke database
def save_to_mssql_passport(data):
    connection_string = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
    )

    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query = """
        EXEC SaveToOCRPASSPORT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        """
        cursor.execute(query, (
            data["dateOfBirth"], data["expiryDate"], data["givenNames"], data["issueDate"], 
            data["issuingStateCode"], data["nationality"], data["passportNo"], data["placeOfBirth"], 
            data["sex"], data["surname"], data["type"]
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

# Fungsi untuk check existing nik
def match_nik_in_database(data):
    connection_string = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
    )

    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query = "SELECT nik FROM OCRKTP"
        cursor.execute(query)
        existing_niks = [row[0] for row in cursor.fetchall()]

        extracted_nik = data["idNumber"]
        if extracted_nik not in existing_niks:
            save_to_mssql_ktp(data)
        
        conn.commit()
        cursor.close()
        conn.close()
    
    except Exception as e:
        print(f"Database error: {e}")

# Fungsi untuk memformat data yang diekstrak
def formatted_extract_data_ktp(data_ktp: str) -> dict:
    if not data_ktp.strip():
        return {
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find any KTP field in the uploaded picture",
            "data": None,
        }

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
                    raw_date = match.group(2).strip()
                    extracted_data["birthday"] = datetime.strptime(raw_date, "%d-%m-%Y").strftime("%Y/%m/%d")
            else:
                # Jika ada koma, pisahkan seperti biasa
                place, date = birth_info.split(",", 1)
                extracted_data["placeOfBirth"] = place.strip()
                raw_date = match.group(2).strip()
                extracted_data["birthday"] = datetime.strptime(raw_date, "%d-%m-%Y").strftime("%Y/%m/%d")
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
        return {
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find KTP field in uploaded picture",
            "data": None,
        }
    
    return {
        "code": "SUCCESS",
        "message": "OK",
        "data": extracted_data,
    }

def format_extracted_data_faktur(data_faktur: str) -> dict:

    if not data_faktur.strip():
        return {
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find Faktur field in uploaded picture.",
            "data": None,
        }
    
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
        return {
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find Faktur field in uploaded picture.",
            "data": None,
        }
    
    response_faktur = {
        "code": "SUCCESS",
        "message": "OK",
        "data": extracted_data_faktur,
    }

    return response_faktur

def format_extracted_data_passport(data_passport: str) -> dict:

    if not data_passport.strip():
        return {
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find Passport field in uploaded picture.",
            "data": None,
        }
    
    lines = data_passport.strip().split("\n")

    extracted_data_passport = {
        "dateOfBirth": None,
        "expiryDate": None,
        "givenNames": None,
        "issueDate": None,
        "issuingStateCode": None,
        "nationality": None,
        "passportNo": None,
        "placeOfBirth": None,
        "sex": None,
        "surname": None,
        "type": None,
    }

    for line in lines:
        if "Date of birth:" in line:
            extracted_data_passport["dateOfBirth"] = line.split(":")[1].strip()
        elif "Expiry date:" in line:
            extracted_data_passport["expiryDate"] = line.split(":")[1].strip()
        elif "Given names:" in line:
            extracted_data_passport["givenNames"] = line.split(":")[1].strip()
        elif "Date of issue:" in line:
            extracted_data_passport["issueDate"] = line.split(":")[1].strip()
        elif "Issuing state code:" in line:
            extracted_data_passport["issuingStateCode"] = line.split(":")[1].strip()
        elif "Nationality:" in line:
            extracted_data_passport["nationality"] = line.split(":")[1].strip()
        elif "Passport no:" in line:
            extracted_data_passport["passportNo"] = line.split(":")[1].strip()
        elif "Place of birth:" in line:
            extracted_data_passport["placeOfBirth"] = line.split(":")[1].strip()
        elif "Sex:" in line:
            extracted_data_passport["sex"] = line.split(":")[1].strip()
        elif "Surname:" in line:
            extracted_data_passport["surname"] = line.split(":")[1].strip()
        elif "Type:" in line:
            extracted_data_passport["type"] = line.split(":")[1].strip()

    if all(value is None for value in extracted_data_passport.values()):
        return {
            "code": "OCR_NO_RESULT",
            "message": "OCR check failed, unable to find Passport field in uploaded picture.",
            "data": None,
        }
    
    response_passport = {
        "code": "SUCCESS",
        "message": "OK",
        "data": extracted_data_passport,
    }

    return response_passport


# Fungsi untuk parsing teks menjadi key-value
def parse_to_key_value(text):
    data = {}
    # Membagi teks berdasarkan baris dan memisahkan key-value menggunakan regex
    for line in text.split("\n"):
        match = re.match(r"^(.*?):\s*(.*)$", line.strip())
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            data[key] = value
    return data

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

    if file.filename.lower().endswith(valid_content_types) or file.mimetype in valid_content_types:
        img = cv2.imdecode(np.fromstring(request.files['file'].read(), np.uint8), cv2.IMREAD_UNCHANGED)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        th, threshed = cv2.threshold(gray, 127, 255, cv2.THRESH_TRUNC)
        result = pytesseract.image_to_string((threshed), lang='ind')
        result.replace('\n', ' ')
        valid = False

        if 'NIK' or "nik" in result:
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

                print(response.usage_metadata)
                
                extracted_data = formatted_extract_data_ktp(response.text)

                if extracted_data["code"] == "SUCCESS":
                    match_nik_in_database(extracted_data["data"])

                return jsonify(extracted_data), 200

            except Exception as e:
                return jsonify({
                    "code": "SERVER_ERROR",
                    "message": str(e),
                    "data": None,
                }), 500

        else:
            return {
                "result": valid,
                "code": "OCR_NO_RESULT",
                "message": "OCR check failed, unable to find NIK in uploaded picture."
            }
        
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

        print(response_faktur.usage_metadata)
        
        extracted_data_faktur = format_extracted_data_faktur(response_faktur.text)

        if extracted_data_faktur["code"] == "SUCCESS":
            save_to_mssql_faktur(extracted_data_faktur["data"])

        return jsonify(extracted_data_faktur), 200

    except Exception as e:
        return jsonify({
            "code": "SERVER_ERROR",
            "message": str(e),
            "data": None,
        }), 500

@app.route("/extract-data-passport", methods=["POST"])
def extract_passport():
    if "file" not in request.files:
        return jsonify({
            "code": "NO_FILE",
            "message": "No file uploaded.",
            "data": None,
        }), 400
    
    file_passport = request.files["file"]

    try:
        passport = Image.open(file_passport)

        # Menggunakan model untuk ekstraksi konten
        response_passport = model.generate_content(
            ["""Analisa dan Ekstrak semua informasi dalam passport dengan format berikut: 
            Date of birth:
            Expiry date:
            Given names:
            Date of issue:
            Issuing state code:
            Nationality:
            Passport no:
            Place of birth:
            Sex:
            Surname:
            Type:

            jangan tambahkan apapun yang tidak perlu seperti simbol, tanda baca, dll. hanya tulisan saja.
            """, passport])
        print(response_passport.usage_metadata)

        formatted_passport = format_extracted_data_passport(response_passport.text)

        if formatted_passport["code"] == "SUCCESS":
            save_to_mssql_passport(formatted_passport["data"])

        return jsonify (formatted_passport), 200
        # return response_passport.text

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
            ["""Extract key-value pairs from this text. Translate all to english
             Do not add anything else
             """, anything])
        
        print(response_anything.usage_metadata)
        
        # Mendapatkan teks dari response
        text = response_anything.text

        # Parsing teks menjadi key-value pairs
        parsed_data = parse_to_key_value(text)  

        response_data_anything = {
            "code": "SUCCESS",
            "message": "OK",
            "data": parsed_data
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
