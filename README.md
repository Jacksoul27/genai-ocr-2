Proses Install

1. Buat virtual environment python (python 3.10 >)
    "python -m venv env" lalu aktifkan env nya "./env/Scripts/activate"

    jika sudah ada env maka aktifkan saja dengan "source env/bin/activate" (untuk linux/mac) atau
    "env\Scripts\activate" (untuk windows)

2. Install depedencies yang ada di "Requirements.txt" ke env yang telah dibuat.
   "pip install -r requirements.txt" atau install satu persatu secara manual.

3. Jika semua depedencies sudah terinstall, adjust path dalam kode lalu run.
   "python app-ktp-uat.py"

4. jika terjadi error, sesuaikan versi depedencies yang diinstall.

5. Sesuaikan path untuk file yang ada di folder "SSL".


How to run

1. Run aplikasi dengan command.
   "python app-ktp-uat.py"

2. Gunakan URL dan route untuk proses ekstraksi KTP di postman dengan request POST

3. Input file ke body dengan form data. Isi key dengan "file" dan tipe nya File. Lalu Upload gambar yang ingin di ekstrak.

4. Send request.

5. Output response berupa json.