import logging
import threading
import os

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

from src.database.db_manager import db, DownloadedItem
# CD_BURN_STATUS_MANAGER is still imported as it's a global singleton,
# but CDBurningService itself will be accessed via current_app.extensions.
from src.cd_burning_service import CD_BURN_STATUS_MANAGER


# Initialize logger for this blueprint
logger = logging.getLogger(__name__)

# Define the Blueprint
cd_burning_bp = Blueprint('cd_burning_bp', __name__, url_prefix='/api/cd-burner')


@cd_burning_bp.route('/status', methods=['GET'])
def get_burner_status():
    """
    Endpoint to check the status of the CD burner and any ongoing burning operation.
    The status is retrieved from the global CD_BURN_STATUS_MANAGER.
    """
    logger.info("Received request for CD burner status.")
    try:
        current_status = CD_BURN_STATUS_MANAGER.get_status()
        logger.debug(f"Current CD burner status: {current_status}")
        return jsonify(current_status), 200
    except Exception as e:
        logger.exception("Error checking CD burner status.")
        # Provide a more robust error response structure
        return jsonify({
            'is_burning': False,
            'current_status': 'Error',
            'progress_percentage': 0,
            'last_error': f"Failed to retrieve burner status: {str(e)}"
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
        return jsonify({"error": "Missing 'download_item_id' in request payload."}), 400

    # Prevent concurrent burns
    if CD_BURN_STATUS_MANAGER.is_burning():
        logger.warning("Attempted to start burn while another is in progress.")
        return jsonify({"error": "A CD burning process is already active. Please wait."}), 409 # Conflict

    try:
        # Fetch the DownloadedItem from the database
        downloaded_item = db.session.get(DownloadedItem, download_item_id)

        if not downloaded_item:
            logger.warning(f"DownloadedItem with ID {download_item_id} not found.")
            return jsonify({"error": f"Downloaded item with ID {download_item_id} not found."}), 404

        content_dir = downloaded_item.local_path

        if not content_dir or not os.path.isdir(content_dir):
            logger.error(f"Content directory not found or invalid: {content_dir} for item ID {download_item_id}")
            return jsonify({"error": "Associated content directory not found or is invalid."}), 404

        # Mark as burning and update initial status
        CD_BURN_STATUS_MANAGER.start_burn(
            status=f"Initiating burn for '{downloaded_item.title}'...",
            progress=0
        )

        # Access the already initialized CDBurningService instance from app.extensions
        # This assumes app.extensions['cd_burning_service'] is set in your create_app() function.
        cd_burner = current_app.extensions.get('cd_burning_service')

        if not cd_burner:
            error_msg = "CD Burning Service not initialized in app.extensions."
            logger.error(error_msg)
            CD_BURN_STATUS_MANAGER.set_error(error_msg)
            return jsonify({"error": "Server error: CD Burning Service not available."}), 500

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
        CD_BURN_STATUS_MANAGER.set_error(f"An unexpected error occurred: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
