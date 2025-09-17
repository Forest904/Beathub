import os
import threading
import logging
import time
from typing import List, Dict, Optional, Tuple

# We rely on comtypes to access IMAPI v2 COM interfaces
try:
    import comtypes
    import comtypes.client as cc
    from ctypes import wintypes, POINTER, byref, c_void_p, windll
except Exception as e:  # pragma: no cover - runtime import
    comtypes = None
    cc = None


class IMAPIUnavailableError(RuntimeError):
    pass


_THREAD_STATE = threading.local()


def _ensure_com_initialized():
    """Ensure COM is initialized for the current thread."""
    if getattr(_THREAD_STATE, 'com_initialized', False):
        return
    if comtypes is None:
        raise IMAPIUnavailableError("comtypes is not available. Install 'comtypes' and run on Windows.")
    try:
        comtypes.CoInitialize()
    except OSError as exc:
        # RPC_E_CHANGED_MODE (0x80010106) indicates COM already initialized in a different mode; ignore
        if getattr(exc, 'winerror', None) not in (None, -2147417850):
            raise
    _THREAD_STATE.com_initialized = True


def _ensure_imapi_available():
    if cc is None:
        raise IMAPIUnavailableError(
            "comtypes is not available. Install 'comtypes' and run on Windows.")


def _create_stream_on_file(path: str):
    """Create an IStream on a file for IMAPI using SHCreateStreamOnFileEx."""
    # Late import to avoid import cost unless needed
    import comtypes
    IStream = comtypes.IStream  # provided by comtypes

    # SHCreateStreamOnFileEx signature
    # HRESULT SHCreateStreamOnFileEx(
    #   PCWSTR pszFile,
    #   DWORD grfMode,
    #   DWORD dwAttributes,
    #   BOOL fCreate,
    #   IStream *pstmTemplate,
    #   IStream **ppstm
    # );
    SHC = windll.shlwapi.SHCreateStreamOnFileEx
    SHC.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                    wintypes.BOOL, c_void_p, POINTER(c_void_p)]
    SHC.restype = wintypes.HRESULT

    # STGM flags (subset)
    STGM_READ = 0x00000000
    STGM_SHARE_DENY_NONE = 0x00000040
    grfMode = STGM_READ | STGM_SHARE_DENY_NONE

    ppstm = c_void_p()
    hr = SHC(path, grfMode, 0, False, None, byref(ppstm))
    if hr < 0:
        raise OSError(f"SHCreateStreamOnFileEx failed, HRESULT=0x{hr & 0xFFFFFFFF:08X}")
    # Cast to IStream*
    return comtypes.cast(ppstm, POINTER(IStream))


class _AudioBurnEvents:
    """Event sink for IDiscFormat2AudioCD progress events."""

    def __init__(self, *, logger: logging.Logger, session, publisher, cancel_flag: threading.Event):
        self._logger = logger
        self._session = session
        self._publisher = publisher
        self._cancel_flag = cancel_flag

    # The method name must match the dispinterface in the IMAPI2 type library.
    # In IMAPI2, the DDiscFormat2Events interface raises an Update event with IDiscFormat2EventArgs.
    def Update(self, object, event_args):  # noqa: N802 - COM event signature
        try:
            # Not all fields are guaranteed; guard each access
            pct = None
            action = None
            try:
                pct = int(getattr(event_args, 'PercentComplete'))
            except Exception:
                pass
            try:
                action = getattr(event_args, 'CurrentAction')
            except Exception:
                pass

            if pct is not None:
                # Map 60..100 for the actual burning phase
                pct_safe = max(0, min(100, int(pct)))
                total = 60 + (pct_safe * 40) // 100
                self._session.update_status("Burning Disc...", progress=total)
                if self._publisher is not None:
                    try:
                        self._publisher.publish({
                            'event': 'cd_burn_progress',
                            'status': 'burning',
                            'phase': 'burning',
                            'progress': total,
                            'action': int(action) if isinstance(action, (int,)) else None,
                            'session_id': self._session.id,
                        })
                    except Exception:
                        pass

            if self._cancel_flag.is_set():
                try:
                    # Attempt best-effort cancellation if supported
                    cancel = getattr(object, 'CancelWrite', None)
                    if callable(cancel):
                        cancel()
                        self._logger.warning("IMAPI burn canceled by request.")
                except Exception:
                    pass
        except Exception:
            # Swallow any event sink exception to avoid tearing down COM connection
            pass


class IMAPI2AudioBurner:
    """
    Minimal IMAPI v2 Audio CD burner using comtypes.

    Responsibilities:
    - Enumerate devices (IDiscMaster2 + IDiscRecorder2)
    - Prepare and burn Red Book Audio CD (44.1kHz/16-bit/stereo WAV streams)
    - Optional CD-TEXT (album + per-track) when properties are available
    - Publish progress via IMAPI2 events and support cancellation
    """

    def __init__(self, logger: Optional[logging.Logger] = None, client_name: str = "CD-Collector"):
        _ensure_imapi_available()
        _ensure_com_initialized()
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._client_name = client_name
        # Create master on-demand to keep COM init light
        self._disc_master = None

    # --- Device management ---
    def _get_master(self):
        if self._disc_master is None:
            self._disc_master = cc.CreateObject('IMAPI2.MsftDiscMaster2')
        return self._disc_master

    def list_recorders(self) -> List[Dict[str, object]]:
        master = self._get_master()
        devices = []
        try:
            count = int(getattr(master, 'Count'))
        except Exception:
            count = 0
        for i in range(count):
            try:
                unique_id = master.Item(i)
                rec = cc.CreateObject('IMAPI2.MsftDiscRecorder2')
                rec.InitializeDiscRecorder(unique_id)
                info = {
                    'unique_id': unique_id,
                    'vendor_id': getattr(rec, 'VendorId', ''),
                    'product_id': getattr(rec, 'ProductId', ''),
                    'product_rev': getattr(rec, 'ProductRevision', ''),
                    'volume_paths': tuple(getattr(rec, 'VolumePathNames', []) or []),
                }
                devices.append(info)
            except Exception as e:
                self._logger.warning("Failed to initialize recorder %s: %s", i, e)
        return devices

    def open_recorder(self, unique_id: Optional[str] = None):
        master = self._get_master()
        if unique_id is None:
            # default: first available
            cnt = int(getattr(master, 'Count'))
            if cnt < 1:
                raise RuntimeError("No optical recorders found via IMAPI2")
            unique_id = master.Item(0)
        rec = cc.CreateObject('IMAPI2.MsftDiscRecorder2')
        rec.InitializeDiscRecorder(unique_id)
        return rec, unique_id

    # --- Burn flow ---
    def check_audio_disc_ready(self, recorder) -> Tuple[bool, bool]:
        """Return (present, writable) for current media using AudioCD format checks."""
        fmt = cc.CreateObject('IMAPI2.MsftDiscFormat2AudioCD')
        try:
            setattr(fmt, 'ClientName', self._client_name)
        except Exception:
            pass
        # Prefer property assignment if supported
        try:
            setattr(fmt, 'Recorder', recorder)
        except Exception:
            try:
                fmt.SetActiveDiscRecorder(recorder)
            except Exception:
                pass

        present = False
        writable = False
        try:
            # These checks may throw if no media present
            is_supported = bool(fmt.IsRecorderSupported(recorder))
            media_ok = bool(fmt.IsCurrentMediaSupported(recorder))
            present = is_supported or media_ok
            writable = media_ok
        except Exception:
            # Any failure here typically means no media / unsupported
            present = False
            writable = False
        return present, writable

    def _apply_cdtext(self, fmt, *, album: Optional[Dict[str, str]] = None, tracks: Optional[List[Dict[str, str]]] = None):
        # Best-effort: these properties may exist depending on OS version
        if album:
            for k_src, k_dst in (("artist", "AlbumArtist"), ("title", "AlbumTitle")):
                val = album.get(k_src)
                if val:
                    for name in (f'put_{k_dst}', k_dst):
                        try:
                            setattr(fmt, k_dst, val) if name == k_dst else getattr(fmt, name)(val)
                            break
                        except Exception:
                            continue
        if tracks:
            for idx, t in enumerate(tracks):
                title = t.get('title')
                artist = t.get('artist')
                if title:
                    for name in ("set_TrackTitle", "SetTrackTitle", "SetTrackText", "put_TrackTitle"):
                        try:
                            getattr(fmt, name)(idx, title)
                            break
                        except Exception:
                            continue
                if artist:
                    for name in ("set_TrackArtist", "SetTrackArtist", "SetTrackPerformer", "put_TrackArtist"):
                        try:
                            getattr(fmt, name)(idx, artist)
                            break
                        except Exception:
                            continue

    def burn_audio_cd(self,
                       *,
                       recorder,
                       wav_paths: List[str],
                       album_cdtext: Optional[Dict[str, str]] = None,
                       per_track_cdtext: Optional[List[Dict[str, str]]] = None,
                       session,
                       publisher,
                       cancel_flag: Optional[threading.Event] = None) -> None:
        if cancel_flag is None:
            cancel_flag = threading.Event()

        if not wav_paths:
            raise ValueError("No WAV tracks provided for burning")

        fmt = cc.CreateObject('IMAPI2.MsftDiscFormat2AudioCD')
        # Assign recorder
        try:
            setattr(fmt, 'Recorder', recorder)
        except Exception:
            fmt.SetActiveDiscRecorder(recorder)
        try:
            setattr(fmt, 'ClientName', self._client_name)
        except Exception:
            pass

        # Best-effort CD-TEXT
        try:
            self._apply_cdtext(fmt, album=album_cdtext, tracks=per_track_cdtext)
        except Exception as e:
            self._logger.warning("CD-TEXT assignment skipped: %s", e)

        # Hook progress events (best-effort)
        conn = None
        try:
            sink = _AudioBurnEvents(logger=self._logger, session=session, publisher=publisher, cancel_flag=cancel_flag)
            conn = cc.GetEvents(fmt, sink)
        except Exception as e:
            self._logger.warning("IMAPI events not available: %s", e)

        # Add tracks (staging phase 50..60)
        stage_start = time.perf_counter()
        for i, p in enumerate(wav_paths):
            if cancel_flag.is_set():
                raise RuntimeError("Burn canceled")
            if not os.path.exists(p):
                raise FileNotFoundError(p)
            try:
                t0 = time.perf_counter()
                stream = _create_stream_on_file(p)
                fmt.AddAudioTrack(stream)
                # Update conversion -> preparation progress: 50% + small step
                prep_prog = 50 + int((i + 1) / max(1, len(wav_paths)) * 10)
                session.update_status(f"Staging tracks ({i+1}/{len(wav_paths)})", progress=prep_prog)
                if publisher is not None:
                    try:
                        publisher.publish({
                            'event': 'cd_burn_progress',
                            'status': 'staging',
                            'phase': 'staging',
                            'progress': prep_prog,
                            'message': f'Staging {i+1}/{len(wav_paths)}',
                            'track_index': i + 1,
                            'track_total': len(wav_paths),
                            'elapsed_sec': round(time.perf_counter() - t0, 2),
                            'session_id': session.id,
                        })
                    except Exception:
                        pass
            except Exception as e:
                raise RuntimeError(f"Failed to stage track {i+1}: {e}")

        # Start burn
        session.update_status("Burning Disc...", progress=60)
        try:
            total_stage = time.perf_counter() - stage_start
            self._logger.info("Staged %d tracks in %.2fs", len(wav_paths), total_stage)
        except Exception:
            pass
        try:
            # Some builds expose Write() with no args; others require Write(variant)
            write = getattr(fmt, 'Write')
            try:
                write(None)  # type: ignore[arg-type]
            except TypeError:
                write()
        except Exception as e:
            # If cancellation occurred, surface a friendly message
            if cancel_flag.is_set():
                raise RuntimeError("Burn canceled by user")
            raise RuntimeError(f"IMAPI2 write failed: {e}")
        finally:
            try:
                if conn is not None:
                    conn.disconnect()
            except Exception:
                pass

        session.update_status("Burning Completed", progress=100)


__all__ = [
    'IMAPI2AudioBurner',
    'IMAPIUnavailableError',
]
