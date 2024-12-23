from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
from PIL import ImageFile, Image
import tempfile
import cv2
import numpy as np
import ssl
import re
import magic
from werkzeug.utils import secure_filename
import os
import requests
import pyodbc
import pytesseract
import ocropencv as ocr
from datetime import datetime
import time
import psutil



load_dotenv()

DB_DRIVER = os.getenv("DB_DRIVER")
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# Inisialisasi Flask
app = Flask(__name__)

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
        print(f"Database error2: {e}")

# Fungsi untuk check existing nik
def match_nik_in_database(nik):
    # Define the connection string using environment variables
    connection_string = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
    )

    try:
        # Establish connection to the database
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Execute the stored procedure with the provided NIK
        query = "exec SelectAllKtp ?"
        cursor.execute(query, nik)

        # Fetch all rows from the executed query
        rows = cursor.fetchall()

        # Check if rows are empty
        if len(rows) == 0:
            print("No data found in the database.")
            return {
                "error": False,
                "message": "Nik not found in database",
                "data": None
            }
        
        else:
            
            # Extract NIKs from the result rows (assuming the NIK is in the first column)
            existing_niks = [row[0] for row in rows]
            # print(rows[0][1])

            # Check if the provided NIK is in the list of existing NIKs
            if nik not in existing_niks:
                return {
                    "error": False,
                    "message": "Nik not found in database",
                    "data": None
                }
            else:
                exist_data = {
                "idNumber": rows[0][0],
                "name": rows[0][1],
                "bloodType": rows[0][2],
                "religion": rows[0][3],
                "gender": rows[0][4],
                "birthPlaceBirthday": rows[0][5],
                "province": rows[0][6],
                "city": rows[0][7],
                "district": rows[0][8],
                "village": rows[0][9],
                "rtrw": rows[0][10],
                "occupation": rows[0][11],
                "expiryDate": rows[0][12],
                "nationality": rows[0][13],
                "maritalStatus": rows[0][14],
                "address": rows[0][15],
                "placeOfBirth": rows[0][16],
                "birthday": rows[0][17],
                }

                print(f"DATA YANG SUDAH ADA {exist_data}")

                # Commit transaction and close connections
                conn.commit()
                cursor.close()
                conn.close()

                return {
                    "error": False,
                    "message": "Nik found in database",
                    "data": exist_data,  # Return the index of the found NIK
                }
        
    except Exception as e:
        # Handle any errors and print them
        print(f"Database error: {e}")
        return {
            "error": True,
            "message": str(e),
            "data": None
        }

# Ekstrak with OpenCV
def extract_ktp_ocr():
    try:
        # Reset posisi file
        request.files['file'].seek(0)

        # Membaca file
        imagefile = request.files['file'].read()
        if not isinstance(imagefile, bytes):
            return {
                'error': True,
                'message': 'File yang diunggah tidak valid.',
                'result': None
            }, 400

        mime_type = magic.Magic(mime=True).from_buffer(imagefile)
        if mime_type not in ['image/jpeg', 'image/png']:
            return {
                'error': True,
                'message': f'Format file tidak didukung: {mime_type}. Hanya JPEG dan PNG yang diterima.',
                'result': None
            }, 400

        # Konversi byte buffer ke array NumPy
        npimg = np.frombuffer(imagefile, np.uint8)
        image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)


        # Validasi apakah gambar berhasil didecode
        if image is None:
            return {
                'error': True,
                'message': 'Gagal mendekode gambar. Pastikan format file adalah JPEG/PNG.',
                'result': None
            }, 400

        # Melakukan OCR pada gambar
        try:
            ocr_results = ocr.main(image)
        except Exception as e:
            return {
                'error': True,
                'message': f'OCR gagal diproses: {str(e)}',
                'result': None
            }, 500

        # Validasi hasil OCR
        if len(ocr_results) < 15:
            return {
                'error': True,
                'message': 'Gagal mengekstrak data menggunakan OCR.',
                'result': False
            }, 400

        # Parsing hasil OCR
        try:
            (nik) = ocr_results
        except ValueError:
            return {
                'error': True,
                'message': 'Format hasil OCR tidak sesuai.',
                'result': False
            }, 400
        
        print(f"Extracted NIK: {nik}")

        # Validasi NIK
        if not nik:
            return {
                'error': True,
                'message': 'Gagal mengekstrak NIK menggunakan OCR.',
                'result': False
            }, 400

        return {
            'error': False,
            'message': 'Proses OCR berhasil.',
            'result': {
                'match': True,
                'nik': nik
            }
        }, 200

    except Exception as e:
        return {
            'error': True,
            'message': f'Error saat melakukan OCR: {str(e)}',
            'result': None
        }, 500
    
@app.route('/processing-ktp', methods=['POST'])
def process_ktp():
    extracted_data = None

    if "file" not in request.files:
        return jsonify({
            "code": "NO_FILE",
            "message": "No file uploaded.",
            "data": None,
        }), 400
    
    file = request.files["file"]    
    pathFolder = "./preprocessing-image/temp-images/"
    os.makedirs(pathFolder, exist_ok=True)

    file.save(pathFolder + file.filename)
    temp_file_path = pathFolder + file.filename
    print(temp_file_path)

    if file.filename == "":
        return jsonify({
            "code": "NO_FILE",
            "message": "No file uploaded.",
            "data": None,
        }), 400
    
    valid_extensions = (".jpg", ".jpeg", ".png")
    valid_content_types = ("image/jpg", "image/jpeg", "image/png")

    if not file.filename.lower().endswith(valid_extensions) or file.mimetype not in valid_content_types:
        return jsonify({
            "code": "IMAGE_INVALID_FORMAT",
            "message": "Invalid image format. Use jpeg/jpg/png.",
            "data": None,
        }), 400
    
    # Membaca file gambar menggunakan OpenCV
    if file.filename.lower().endswith(valid_content_types) or file.mimetype in valid_content_types:
        file.seek(0)
        image_data = np.fromfile(temp_file_path, np.uint8)  # Baca file ke array NumPy
        image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

        result_raw, id_number = ocr.ocr_raw(image)

        print(f"raw data: {result_raw}, {id_number}")

        if 'NIK' in result_raw or 'nik' in result_raw:
                try:
                    image = Image.open(file.stream)
                    width, height = image.size
                    
                    # Validasi ukuran gambar
                    if width < 256 or height < 256 or width > 4096 or height > 4096:
                        return jsonify({
                            "code": "IMAGE_INVALID_SIZE",
                            "message": "Invalid image dimensions.",
                            "data": None,
                        }), 400

                    # Validasi apakah gambar adalah fotokopi
                    if is_photocopy(image):
                        return jsonify({
                            "code": "IMAGE_IS_PHOTOCOPY",
                            "message": "Image appears to be a photocopy.",
                            "data": None,
                        }), 400
                    
                    
                    # Ekstraksi data NIK dengan OCR eksternal
                    ocr_response, status_code_response = extract_ktp_ocr()

                    if ocr_response['error']:
                        return jsonify({
                            "code": "OCR_FAILED",
                            "message": ocr_response['message'],
                            "data": None
                        }), status_code_response
                    
                    # Pencocokan NIK di database
                    match_response= match_nik_in_database(ocr_response['result']['nik'])

                    if match_response['error']:
                        return jsonify({
                            "code": "NIK_MATCH_FAILED",
                            "message": match_response['message'],
                            "data": None
                        })

                    if match_response['message'] == "Nik not found in database":

                        url = "http://127.0.0.1:5000/extract-data-ktp"

                        # payload = {}

                        with open(temp_file_path, 'rb') as file_to_send:
                            try:
                                # Send POST request to another server for processing
                                response = requests.post(url, files={'file': file_to_send})
                                
                                if response.status_code != 200:
                                    return jsonify({
                                        "code": "EXTERNAL_OCR_ERROR",
                                        "message": "Failed to extract data from external OCR service.",
                                        "data": response.text,
                                    }), response.status_code

                                # Ekstrak dan simpan data
                                extracted_data = formatted_extract_data_ktp(response.text)
                                # print(response.text['data'])
                                print(extracted_data['data'])
                                save_to_mssql_ktp(extracted_data['data'])
                            
                            except requests.exceptions.RequestException as e:
                                return jsonify({
                                    "code": "EXTERNAL_REQUEST_ERROR",
                                    "message": str(e),
                                    "data": None,
                                }), 500
                    
                    else:

                        # Jika NIK ditemukan, gunakan "data" dari match_response
                        exist_data = match_response['data']
                        
                        if os.path.exists(temp_file_path):
                            file.stream.close()
                            os.remove(temp_file_path)

                        return {
                            "code": "OK",
                            "message": "Data exist.",
                            "data": exist_data,
                        }
                                
                except Exception as e:
                    return jsonify({
                        "code": "SERVER_ERROR",
                        "message": str(e),
                        "data": None,
                    }), 500
        else:
            return jsonify({
                "code": "OCR_NO_RESULT",
                "message": "OCR check failed, unable to find NIK in uploaded picture.",
                "data": None
            }), 400
        
    if os.path.exists(temp_file_path):
        file.stream.close()
        os.remove(temp_file_path)
            
    return (extracted_data), 200

if __name__ == "__main__":
    cert_file = "./SSL/bundle.crt"
    key_file = "./SSL/csr.key"

    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    
    app.run(host='0.0.0.0', port=5000, ssl_context=context)