# src/routes/cd_burning_routes.py

import logging
import threading # Used for running the burning process in a separate thread
import os # For path manipulation if needed, though local_path from DB will be key

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError # For database query errors

# Import the DownloadedItem model to query download details
from database.db_manager import db, DownloadedItem

# Import the new CD Burning Service
# We will create this file next, but it's good to define the import now.
from src.cd_burning_service import CDBurningService, CD_BURN_STATUS_MANAGER


# Initialize logger for this blueprint
logger = logging.getLogger(__name__)

# Define the Blueprint
cd_burning_bp = Blueprint('cd_burning_bp', __name__, url_prefix='/api/cd-burner')

# --- Global State for Concurrency Control (for prototype simplicity) ---
# In a production app, this would be managed by a task queue (e.g., Celery)
# or a more robust state management system (e.g., Redis).
# For now, a simple dictionary to hold the service instance and its status.
# We'll put this into a dedicated manager class later, but for now,
# a placeholder comment to remember.

# This dictionary will store the state of the burning process.
# We'll refine this into a class/singleton in cd_burning_service.py
# For now, imagine it holds:
# {
#   'is_burning': False,
#   'current_status': 'Idle', # e.g., 'Detecting Burner', 'Ready', 'Converting WAVs', 'Burning Disc', 'Completed', 'Error: Message'
#   'progress_percentage': 0,
#   'last_error': None
# }
# For now, let's just make it a global placeholder or assume it comes from the service.


@cd_burning_bp.route('/status', methods=['GET'])
def get_burner_status():
    """
    Endpoint to check the status of the CD burner and any ongoing burning operation.
    """
    logger.info("Received request for CD burner status.")
    try:
        # Initialize the service if it hasn't been already (e.g., first request)
        # This is a bit simplistic; ideally, the service would be initialized once
        # with the app or stored in app.extensions if it holds state.
        # For our prototype, let's assume CD_BURN_STATUS_MANAGER will handle
        # accessing the shared status.
        # We'll properly initialize the service object in app.py later.

        # Retrieve status from the global status manager defined in cd_burning_service.py
        current_status = CD_BURN_STATUS_MANAGER.get_status()
        logger.debug(f"Current CD burner status: {current_status}")

        return jsonify(current_status), 200

    except Exception as e:
        logger.exception("Error checking CD burner status.")
        return jsonify({
            'is_burning': False,
            'current_status': 'Error',
            'progress_percentage': 0,
            'last_error': f"Failed to get burner status: {str(e)}"
        }), 500


@cd_burning_bp.route('/burn', methods=['POST'])
def start_cd_burn():
    """
    Endpoint to initiate the CD burning process for a selected downloaded item.
    Expects a JSON payload with 'download_item_id'.
    """
    data = request.get_json()
    download_item_id = data.get('download_item_id')
    logger.info(f"Received request to start CD burn for DownloadedItem ID: {download_item_id}")

    if not download_item_id:
        logger.warning("Missing 'download_item_id' in burn request.")
        return jsonify({"error": "Missing 'download_item_id' in request"}), 400

    # Prevent concurrent burns for the prototype
    if CD_BURN_STATUS_MANAGER.is_burning():
        logger.warning("Attempted to start burn while another is in progress.")
        return jsonify({"error": "A CD burning process is already active. Please wait."}), 409 # Conflict

    try:
        # Fetch the DownloadedItem from the database
        downloaded_item = db.session.get(DownloadedItem, download_item_id) # Using .get() for direct primary key lookup

        if not downloaded_item:
            logger.warning(f"DownloadedItem with ID {download_item_id} not found.")
            return jsonify({"error": f"Downloaded item with ID {download_item_id} not found."}), 404

        # Construct the full path to the content directory
        # The local_path column should already contain the full path to the 'Artist - Album' folder
        content_dir = downloaded_item.local_path

        if not content_dir or not os.path.isdir(content_dir):
            logger.error(f"Content directory not found or invalid: {content_dir} for item ID {download_item_id}")
            return jsonify({"error": "Associated content directory not found or is invalid."}), 404

        # Mark as burning and update initial status
        CD_BURN_STATUS_MANAGER.start_burn(
            status=f"Initiating burn for '{downloaded_item.title}'...",
            progress=0
        )

        # Create an instance of the CD Burning Service
        # We will pass app.logger and the base_output_dir from config to it later.
        # For now, let's just make sure it can be instantiated.
        # We'll pass the logger from current_app for consistency.
        cd_burner = CDBurningService(current_app.logger, current_app.config.get('BASE_OUTPUT_DIR'))

        # Start the burning process in a new thread
        # The thread will update CD_BURN_STATUS_MANAGER directly
        threading.Thread(target=cd_burner.burn_cd, args=(content_dir, downloaded_item.title)).start()
        logger.info(f"CD burning process initiated in background thread for '{downloaded_item.title}'.")

        return jsonify({"status": "Burning started", "message": "CD burning initiated successfully."}), 202 # Accepted

    except SQLAlchemyError as e:
        logger.exception(f"Database error when fetching DownloadedItem ID {download_item_id}.")
        CD_BURN_STATUS_MANAGER.set_error(f"Database error: {str(e)}")
        return jsonify({"error": "Database error during item lookup."}), 500
    except Exception as e:
        logger.exception(f"An unexpected error occurred while initiating CD burn for ID {download_item_id}.")
        CD_BURN_STATUS_MANAGER.set_error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500