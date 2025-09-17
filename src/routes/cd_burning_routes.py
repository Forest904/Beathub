import logging
import threading
import os

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

from src.database.db_manager import db, DownloadedItem
from src.burn_sessions import BurnSessionManager
from src.progress import BrokerPublisher


from src.cd_burning_service import IMAPIUnavailableError
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
        mgr: BurnSessionManager = current_app.extensions.get('burn_sessions')
        if mgr is None:
            return jsonify({"error": "BurnSessionManager not available"}), 503
        session_id = request.args.get('session_id')
        sess = mgr.get(session_id) if session_id else mgr.last()
        if not sess:
            return jsonify({"message": "No burn session"}), 200
        return jsonify(sess.to_dict()), 200
    except Exception as e:
        logger.exception("Error checking CD burner status.")
        return jsonify({"error": f"Failed to retrieve burner status: {str(e)}"}), 500


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

    mgr: BurnSessionManager = current_app.extensions.get('burn_sessions')
    if mgr is None:
        return jsonify({"error": "BurnSessionManager not available"}), 503
    # Prevent concurrent burns (single device policy)
    if mgr.is_any_burning():
        logger.warning("Attempted to start burn while another is in progress.")
        return jsonify({"error": "A CD burning process is already active. Please wait."}), 409

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

        # Create a new session and publisher
        import uuid
        session = mgr.create(title=downloaded_item.title, session_id=str(uuid.uuid4()))
        cd_burner = current_app.extensions.get('cd_burning_service')

        if not cd_burner:
            error_msg = "CD Burning Service not initialized in app.extensions."
            logger.error(error_msg)
            session.set_error(error_msg)
            return jsonify({"error": "Server error: CD Burning Service not available."}), 500

        broker = current_app.extensions.get('progress_broker')
        publisher = BrokerPublisher(broker) if broker else None

        # Start the burning process in a new thread, passing session + publisher
        threading.Thread(
            target=cd_burner.burn_cd,
            args=(content_dir, downloaded_item.title),
            kwargs={"session": session, "publisher": publisher},
        ).start()
        logger.info(f"CD burning process initiated in background thread for '{downloaded_item.title}' (session {session.id}).")

        return jsonify({"status": "accepted", "session_id": session.id, "message": "CD burning initiated."}), 202

    except SQLAlchemyError as e:
        logger.exception(f"Database error when fetching DownloadedItem ID {download_item_id}.")
        try:
            # If session exists, mark error; otherwise ignore
            session.set_error(f"Database error: {str(e)}")  # type: ignore[name-defined]
        except Exception:
            pass
        return jsonify({"error": "Database error during item lookup."}), 500
    except Exception as e:
        logger.exception(f"An unexpected error occurred while initiating CD burn for ID {download_item_id}.")
        try:
            session.set_error(f"An unexpected error occurred: {str(e)}")  # type: ignore[name-defined]
        except Exception:
            pass
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@cd_burning_bp.route('/devices', methods=['GET'])
def list_devices():
    """List optical recorders with dynamic media status (Windows/IMAPI2)."""
    try:
        cd_burner = current_app.extensions.get('cd_burning_service')
        mgr: BurnSessionManager = current_app.extensions.get('burn_sessions')
        if not cd_burner:
            return jsonify({"devices": [], "error": "CD Burning Service not available"}), 503
        try:
            devices = cd_burner.list_devices_with_status()
        except IMAPIUnavailableError as exc:
            logger.warning('IMAPI unavailable while listing devices: %s', exc)
            return jsonify({"devices": [], "error": str(exc)}), 503
        # augment with global busy flag if anything burning
        is_busy = bool(mgr and mgr.is_any_burning())
        for d in devices:
            # if any burn active, mark active device as busy
            if is_busy and d.get('selected'):
                d['active'] = True
        return jsonify({"devices": devices}), 200
    except Exception as e:
        logger.exception("Failed to list devices")
        return jsonify({"devices": [], "error": str(e)}), 500


@cd_burning_bp.route('/cancel', methods=['POST'])
def cancel_burn():
    """Request cancellation of an in-progress burn by session_id."""
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id') or request.args.get('session_id')
        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400

        mgr: BurnSessionManager = current_app.extensions.get('burn_sessions')
        cd_burner = current_app.extensions.get('cd_burning_service')
        if not mgr or not cd_burner:
            return jsonify({"error": "CD Burning Service not available"}), 503
        sess = mgr.get(session_id)
        if not sess:
            return jsonify({"error": "Session not found"}), 404
        if not sess.is_burning:
            return jsonify({"error": "Session not burning"}), 409

        ok = cd_burner.request_cancel(session_id)
        if not ok:
            return jsonify({"error": "Cancel signal not accepted"}), 409
        try:
            sess.update_status("Cancelling...")
        except Exception:
            pass
        return jsonify({"status": "accepted", "message": "Cancellation requested"}), 202
    except Exception as e:
        logger.exception("Error handling cancel request")
        return jsonify({"error": str(e)}), 500


@cd_burning_bp.route('/select-device', methods=['POST'])
def select_device():
    """Select or clear the active recorder by device_id (Windows/IMAPI2)."""
    try:
        data = request.get_json(silent=True) or {}
        has_device_field = 'device_id' in data
        device_id = data.get('device_id') if has_device_field else request.args.get('device_id')

        mgr: BurnSessionManager = current_app.extensions.get('burn_sessions')
        cd_burner = current_app.extensions.get('cd_burning_service')
        if not cd_burner:
            return jsonify({"error": "CD Burning Service not available"}), 503

        # Do not allow selection changes while burning
        if mgr and mgr.is_any_burning():
            return jsonify({"error": "Cannot change device while burning"}), 409

        if has_device_field and (device_id is None or (isinstance(device_id, str) and not device_id.strip())):
            cd_burner.clear_selected_device()
            devices = cd_burner.list_devices_with_status()
            return jsonify({"devices": devices, "selected": None}), 200

        if isinstance(device_id, str):
            device_id = device_id.strip()
        if not device_id:
            return jsonify({"error": "Missing device_id"}), 400

        ok = cd_burner.select_device(device_id)
        if not ok:
            return jsonify({"error": "Failed to select device"}), 400
        devices = cd_burner.list_devices_with_status()
        return jsonify({"devices": devices, "selected": device_id}), 200
    except Exception as e:
        logger.exception("Error selecting device")
        return jsonify({"error": str(e)}), 500
