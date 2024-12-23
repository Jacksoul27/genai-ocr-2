from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/processing-ktp', methods=['POST'])
def process_ktp():

    file = request.files["file"]

    file.save("./temp-images/" + file.filename)

    temp_file = "D:/Development/python/preprocessing-image/temp-images/" + file.filename
    print(temp_file)

    url = "http://127.0.0.1:5000/extract-data-ktp"

     # Open the file for sending
    with open(temp_file, 'rb') as file_to_send:
        try:

            # Send POST request to another server for processing
            response = requests.post(url, files={'file': file_to_send})
            print(response.text)

            # Return the response from the external service
            return jsonify({"message": "File processed successfully", "response": response.text}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)