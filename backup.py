import os
from flask import Flask, request, send_file, render_template
import threading
import webbrowser
import socket

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Define a global variable to store the server URL
server_url = None

# Define a flag to indicate whether the server is running
server_running = threading.Event()


@app.route("/transfer", methods=["POST"])
def transfer_file():
    if "file" not in request.files:
        return "No file part"
    file = request.files["file"]
    if file.filename == "":
        return "No selected file"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], file.filename))
    return "File uploaded successfully"


@app.route("/", methods=["GET"])
def home():
    global server_url
    server_url = request.url_root
    return render_template("index.html", server_url=server_url)


@app.route("/manifest.json")
def serve_manifest():
    return send_file("manifest.json", mimetype="application/manifest+json")


@app.route("/upload", methods=["GET"])
def upload():
    return render_template("uploads.html")


@app.route("/downloads", methods=["GET"])
def show_downloads():
    files = os.listdir(app.config["UPLOAD_FOLDER"])
    download_links = [f"/download/{filename}" for filename in files]
    return render_template("downloads.html", download_links=download_links)


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    return send_file(
        os.path.join(app.config["UPLOAD_FOLDER"], filename), as_attachment=True
    )


@app.route("/shutdown", methods=["GET"])
def shutdown():
    flask_thread.join()  # Wait for Flask thread to complete
    shutdown_server()  # Shutdown Flask server
    return "Server shutting down..."


def get_local_ip():
    return socket.gethostbyname(socket.gethostname())


def start_flask_server():
    global server_url
    local_ip = get_local_ip()
    server_url = (
        f"http://{local_ip}:5000"  # Construct the server URL using local IP address
    )
    server_running.set()  # Set the server running flag
    app.run(host="0.0.0.0", port=5000)


def shutdown_server():
    os._exit(0)  # Exit the application


if __name__ == "__main__":
    # Start the Flask server in a separate thread
    flask_thread = threading.Thread(target=start_flask_server)
    flask_thread.start()

    # Wait until the server is running
    server_running.wait()

    # Open the server URL in the default web browser
    webbrowser.open(server_url)
