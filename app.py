# app.py
import os
import logging

# --- Flask specific imports ---
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# --- Import our refactored modules ---
from src.download_sevice import DownloadService # This is your main controller logic

# --- Logger Configuration ---
# Configure logging for the Flask app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Flask Application Setup ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Initialize the DownloadService with a default output directory
# This is where your core application logic resides
download_service = DownloadService(base_output_dir="./downloads")

@app.route('/')
def serve_index():
    """Serves the main HTML frontend file."""
    # Ensure index.html is in the same directory as app.py
    return send_from_directory('.', 'index.html')

@app.route('/download', methods=['POST'])
def download_spotify_item_api():
    """API endpoint to trigger Spotify content download."""
    data = request.get_json()
    spotify_link = data.get('spotify_link')

    if not spotify_link:
        return jsonify({"status": "error", "message": "Spotify link is required."}), 400

    logger.info(f"Received download request for: {spotify_link}")
    # Delegate the heavy lifting to the DownloadService
    result = download_service.download_spotify_content(spotify_link)

    if result["status"] == "success":
        return jsonify(result), 200
    else:
        # For errors, use 500 Internal Server Error or 400 Bad Request depending on the error type
        status_code = 500 if "unexpected" in result.get("message", "").lower() else 400
        return jsonify(result), status_code

if __name__ == '__main__':
    # Ensure the 'downloads' directory exists when the app starts
    os.makedirs("./downloads", exist_ok=True)
    logger.info("Starting Flask application...")
    # Run the Flask app
    # In a production environment, use a production-ready WSGI server like Gunicorn or uWSGI
    app.run(debug=True, host='0.0.0.0', port=5000)

