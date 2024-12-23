--Proses Install--

Jalankan proses dibawah dalam masing-masing folder (preprocessing-image & service-gemini)

1. Buat virtual environment python (python 3.10 >)
    "python -m venv env" lalu aktifkan env nya "./env/Scripts/activate"

    jika sudah ada env maka aktifkan saja dengan "source env/bin/activate" (untuk linux/mac) atau
    "env\Scripts\activate" (untuk windows)

2. Install depedencies yang ada di "Requirements.txt" ke env yang telah dibuat.
   "pip install -r requirements.txt" atau install satu persatu secara manual.

3. jika terjadi error, sesuaikan versi depedencies yang diinstall.

4. Sesuaikan path untuk file yang ada di folder "SSL".

5. buat file dotenv dengan key:

Folder preprocessing-image:
   - DB_DRIVER
   - DB_SERVER
   - DB_NAME
   - DB_USER
   - DB_PASSWORD

Folder service-gemini:
   - GEMINI_API_KEY

--How to run--

1. Folder "preprocessing-image" merupakan folder utama yang berfungsi untuk pemrosesan gambar dan validasi sebelum gambar dikirimkan 
   ke "service-gemini" untuk diekstrak. jalankan file "preprocessing.py" dalam folder tersebut.
      
      "python preprocessing.py"

2. Folder "service-gemini" adalah service untuk mengekstrak data dari file ktp dengan menggunakan API Gemini, yang kemudian request akan dikirimkan
   dari "preprocessing.py" ke "service-gemini" untuk melakukan ekstraksi data. Jalankan file "app.py" dalam folder tersebut.
   
      "python app.py"

3. Jika ingin melakukan pengujian, buka postman lalu gunakan endpoint yang ada di "preprocessing.py" untuk melakukan request. Contoh endpoint yang ada adalah:

      "172.16.6.85:5000/processing-ktp" sesuaikan kembali IP dan PORT yang digunakan.

   Input file ktp kedalam endpoint tersebut pada "form-data" dengan key dan tipe nya "file", lalu upload ktp yang akan diekstrak dalam field value.

4. Jika code 200, maka berhasil dan akan mengembalikan data dalam format json.