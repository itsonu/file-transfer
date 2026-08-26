import os
import threading
import webbrowser
import socket
from flask import Flask, request, send_file, render_template
import tkinter as tk

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Define a global variable to store the server URL
server_url = None

# Define a flag to indicate whether the server is running
server_running = threading.Event()

# Define a flag to indicate whether the server should be stopped
should_stop_server = threading.Event()


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
    threading.join()  # Wait for Flask thread to complete
    stop_flask_server()  # Shutdown Flask server
    return "Server shutting down..."

# Define other Flask routes here...


def get_local_ip():
    return socket.gethostbyname(socket.gethostname())


def start_flask_server():
    global server_url
    local_ip = get_local_ip()
    server_url = f"http://{local_ip}:5000"
    server_running.set()
    app.run(host="0.0.0.0", port=5000)


def stop_flask_server():
    should_stop_server.set()


def open_browser():
    webbrowser.open(server_url)


def open_browser_gui():

    def open_browser_and_close():
        open_browser()

    def start_server():
        flask_thread = threading.Thread(target=start_flask_server)
        flask_thread.start()
        open_browser_and_close()

    start_server()


if __name__ == "__main__":
    open_browser_gui()
    open_browser()
