from flask import Flask, request, jsonify
import os

app = Flask(__name__)

DOCUMENTS_FOLDER = "documents"

os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)


@app.route("/upload", methods=["POST"])
def upload_file():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    file_path = os.path.join(
        DOCUMENTS_FOLDER,
        file.filename
    )

    file.save(file_path)

    return jsonify({
        "message": "PDF uploaded successfully",
        "filename": file.filename
    }), 200


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )