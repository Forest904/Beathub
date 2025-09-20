import os
import tempfile
import wave
import contextlib
import threading
import logging
import time
from typing import List, Dict, Optional, Tuple

# We rely on comtypes to access IMAPI v2 COM interfaces
try:
    import comtypes
    import comtypes.client as cc
    from ctypes import wintypes, POINTER, byref, c_void_p, windll, memmove, c_size_t
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
    """Create an IStream on a file for IMAPI using SHCreateStreamOnFileEx.

    Some comtypes builds do not expose ``comtypes.IStream`` at the top level.
    To be robust, import fallbacks or define a minimal IStream interface so we
    can type-cast the returned pointer for IMAPI consumption.
    """
    # Late import to avoid import cost unless needed
    import comtypes  # type: ignore
    # Resolve an IStream interface type
    IStream = None  # type: ignore[assignment]
    try:  # Preferred
        IStream = getattr(comtypes, 'IStream')
    except Exception:
        try:  # Fallback location in some versions
            from comtypes.automation import IStream as _AutoIStream  # type: ignore
            IStream = _AutoIStream  # type: ignore[assignment]
        except Exception:
            # Last resort: declare a minimal interface with the correct IID.
            from comtypes import IUnknown, GUID  # type: ignore

            class IStream(IUnknown):  # type: ignore[misc, valid-type]
                _iid_ = GUID('{0000000C-0000-0000-C000-000000000046}')
                _methods_ = []  # We don't invoke methods directly on the stream here

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
    # Some Python builds do not expose wintypes.HRESULT; use ctypes.HRESULT or c_long fallback.
    try:
        from ctypes import HRESULT as _HRESULT
    except Exception:  # pragma: no cover - robustness
        from ctypes import c_long as _HRESULT
    SHC.restype = _HRESULT

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


def _create_stream_on_memory(data: bytes):
    """Create an IStream over the given bytes using CreateStreamOnHGlobal.

    This helps when a few drivers are picky about file-backed streams; a
    memory-backed IStream is broadly compatible.
    """
    import comtypes  # type: ignore
    # Resolve IStream type (reuse logic in _create_stream_on_file)
    try:
        IStream = getattr(comtypes, 'IStream')  # type: ignore[attr-defined]
    except Exception:
        try:
            from comtypes.automation import IStream as _AutoIStream  # type: ignore
            IStream = _AutoIStream
        except Exception:
            from comtypes import IUnknown, GUID  # type: ignore

            class IStream(IUnknown):  # type: ignore[misc, valid-type]
                _iid_ = GUID('{0000000C-0000-0000-C000-000000000046}')
                _methods_ = []

    GMEM_MOVEABLE = 0x0002
    kernel32 = windll.kernel32
    ole32 = windll.ole32

    # Ensure correct prototypes on 64-bit Python to avoid pointer truncation
    try:
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, c_size_t]
        kernel32.GlobalAlloc.restype = c_void_p
        kernel32.GlobalLock.argtypes = [c_void_p]
        kernel32.GlobalLock.restype = c_void_p
        kernel32.GlobalUnlock.argtypes = [c_void_p]
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalFree.argtypes = [c_void_p]
        kernel32.GlobalFree.restype = c_void_p
    except Exception:
        pass

    # Allocate moveable global memory and copy data
    hglobal = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not hglobal:
        raise OSError('GlobalAlloc failed')
    ptr = kernel32.GlobalLock(hglobal)
    if not ptr:
        kernel32.GlobalFree(hglobal)
        raise OSError('GlobalLock failed')
    try:
        memmove(ptr, data, len(data))
    finally:
        kernel32.GlobalUnlock(hglobal)

    # Create the IStream; delete HGLOBAL on release
    ppstm = c_void_p()
    try:
        try:
            from ctypes import HRESULT as _HRESULT
        except Exception:
            from ctypes import c_long as _HRESULT
        ole32.CreateStreamOnHGlobal.argtypes = [c_void_p, wintypes.BOOL, POINTER(c_void_p)]
        ole32.CreateStreamOnHGlobal.restype = _HRESULT
        hr = ole32.CreateStreamOnHGlobal(hglobal, True, byref(ppstm))
        if hr < 0:
            # If creation failed, free memory ourselves
            kernel32.GlobalFree(hglobal)
            raise OSError(f"CreateStreamOnHGlobal failed, HRESULT=0x{hr & 0xFFFFFFFF:08X}")
    except Exception:
        # In case of any exception, ensure memory is freed
        try:
            kernel32.GlobalFree(hglobal)
        except Exception:
            pass
        raise

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

    def __init__(self, logger: Optional[logging.Logger] = None, client_name: str = "BeatHub"):
        _ensure_imapi_available()
        _ensure_com_initialized()
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._client_name = client_name
        # Create master on-demand to keep COM init light
        self._disc_master = None

    # --- Device management ---
    def _get_master(self):
        # Ensure COM is initialized for whichever thread invokes this
        _ensure_com_initialized()
        if self._disc_master is None:
            self._disc_master = cc.CreateObject('IMAPI2.MsftDiscMaster2')
        return self._disc_master

    def list_recorders(self) -> List[Dict[str, object]]:
        # Ensure COM for the current thread before using COM objects
        _ensure_com_initialized()
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
        # Ensure COM for the current thread before using COM objects
        _ensure_com_initialized()
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
        """
        Probe current media and return a tuple (present, writable_for_audio).

        - present: True if any recordable media is present (CD/DVD) that the system
          recognizes for burning. Uses Audio CD first, then falls back to Data format
          to avoid false negatives on some drives/media.
        - writable_for_audio: True only if the inserted media is suitable for Audio CD
          (i.e., blank CD-R/RW recognized by IMAPI2 audio format).
        """
        _ensure_com_initialized()

        # First attempt: Audio CD format (preferred)
        audio_present = False
        audio_writable = False
        try:
            fmt_audio = cc.CreateObject('IMAPI2.MsftDiscFormat2AudioCD')
            try:
                setattr(fmt_audio, 'ClientName', self._client_name)
            except Exception:
                pass
            try:
                setattr(fmt_audio, 'Recorder', recorder)
            except Exception:
                try:
                    fmt_audio.SetActiveDiscRecorder(recorder)
                except Exception:
                    pass
            try:
                # Returns True only when the current media is usable for audio CDs
                audio_writable = bool(fmt_audio.IsCurrentMediaSupported(recorder))
                audio_present = audio_writable
            except Exception:
                audio_present = False
                audio_writable = False
        except Exception:
            # If AudioCD objects fail to create, attempt Track‑At‑Once as a
            # secondary probe for audio-capable blank media; otherwise fall through
            # to data probing below.
            try:
                fmt_tao = cc.CreateObject('IMAPI2.MsftDiscFormat2TrackAtOnce')
                try:
                    setattr(fmt_tao, 'ClientName', self._client_name)
                except Exception:
                    pass
                try:
                    setattr(fmt_tao, 'Recorder', recorder)
                except Exception:
                    try:
                        fmt_tao.SetActiveDiscRecorder(recorder)
                    except Exception:
                        pass
                try:
                    audio_writable = bool(fmt_tao.IsCurrentMediaSupported(recorder))
                    audio_present = audio_writable
                except Exception:
                    audio_present = False
                    audio_writable = False
            except Exception:
                pass

        # Fallback probe: Data format — helps detect presence and blank CD types
        any_present = bool(audio_present)
        try:
            fmt_data = cc.CreateObject('IMAPI2.MsftDiscFormat2Data')
            try:
                setattr(fmt_data, 'ClientName', self._client_name)
            except Exception:
                pass
            try:
                # For Format2Data the COM API exposes a Recorder property setter
                fmt_data.Recorder = recorder  # type: ignore[attr-defined]
            except Exception:
                # As a fallback, try a variant naming (rare)
                try:
                    setattr(fmt_data, 'Recorder', recorder)
                except Exception:
                    pass

            data_writable = False
            data_blank = False
            phys_type = None
            try:
                data_writable = bool(fmt_data.IsCurrentMediaSupported(recorder))
            except Exception:
                pass
            try:
                data_blank = bool(getattr(fmt_data, 'MediaHeuristicallyBlank'))
            except Exception:
                pass
            try:
                phys_type = getattr(fmt_data, 'CurrentPhysicalMediaType')
            except Exception:
                pass

            # Presence considered true if the data formatter sees a supported writable media
            # or we can read a plausible physical media type.
            any_present = any_present or bool(data_writable or (isinstance(phys_type, (int,)) and phys_type != 0))

            # If AudioCD formatter is unavailable on this system, infer audio-writability from
            # data formatter and recorder profile information. Treat CD-R/CD-RW media as
            # acceptable for audio when the data formatter says current media is supported.
            if not audio_present:
                try:
                    if isinstance(phys_type, (int,)) and phys_type in (2, 3) and data_writable:
                        audio_writable = True
                    elif data_blank:
                        # As an additional hint, check the recorder's CurrentProfiles (IMAPI_PROFILE_TYPE)
                        # Values of interest: 0x0009 (CD-R), 0x000A (CD-RW)
                        try:
                            profiles = tuple(getattr(recorder, 'CurrentProfiles', []) or [])
                        except Exception:
                            profiles = ()
                        try:
                            # Normalize to ints
                            profiles_int = []
                            for p in profiles:
                                try:
                                    profiles_int.append(int(p))
                                except Exception:
                                    # Some drivers expose small COM wrappers; best-effort cast
                                    try:
                                        profiles_int.append(int(getattr(p, 'value', 0)))
                                    except Exception:
                                        pass
                            if any(p in (0x0009, 0x000A) for p in profiles_int):
                                audio_writable = True
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            # Creating data formatter failed — ignore
            pass

        return bool(any_present), bool(audio_writable)

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
        _ensure_com_initialized()
        if cancel_flag is None:
            cancel_flag = threading.Event()

        if not wav_paths:
            raise ValueError("No WAV tracks provided for burning")

        # Prefer the AudioCD formatter; if missing on the host, gracefully
        # fall back to Track-At-Once which can also burn Red Book audio.
        using_tao = False
        try:
            fmt = cc.CreateObject('IMAPI2.MsftDiscFormat2AudioCD')
        except OSError as e_audio:
            try:
                fmt = cc.CreateObject('IMAPI2.MsftDiscFormat2TrackAtOnce')
                using_tao = True
                # Let callers know via logs that we're using the fallback path
                try:
                    self._logger.warning(
                        "AudioCD formatter unavailable; falling back to Track-At-Once (TAO)."
                    )
                except Exception:
                    pass
            except Exception as e_tao:
                # When neither Audio CD nor TAO is available (e.g., stripped Windows image),
                # surface a clear and actionable error.
                raise IMAPIUnavailableError(
                    "Windows Audio CD burning components are missing. Tried 'MsftDiscFormat2AudioCD' and TAO fallback. "
                    "Enable 'Windows Media Player' in Optional Features or repair Windows media components, then restart the app."
                ) from (e_tao or e_audio)
        # Assign recorder
        try:
            setattr(fmt, 'Recorder', recorder)
        except Exception:
            fmt.SetActiveDiscRecorder(recorder)
        try:
            setattr(fmt, 'ClientName', self._client_name)
        except Exception:
            pass

        # Best-effort CD-TEXT (supported by both AudioCD and TAO on most systems)
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

        # State kept for cleanup in outer finally
        created_pcm_files: List[str] = []

        # Wrap staging/burn in outer try/finally so TAO media is always released
        try:
            # For Track-At-Once, media must be explicitly prepared before adding tracks
            if using_tao:
                try:
                    prep = getattr(fmt, 'PrepareMedia', None)
                    if callable(prep):
                        prep()
                except Exception as e:
                    raise RuntimeError(f"TAO prepare media failed: {e}")
                # Ensure media is finalized after writing tracks (best-effort)
                try:
                    try:
                        setattr(fmt, 'DoNotFinalizeMedia', False)
                    except Exception:
                        put_finalize = getattr(fmt, 'put_DoNotFinalizeMedia', None)
                        if callable(put_finalize):
                            put_finalize(False)
                except Exception:
                    pass

            # Helper: when using TAO, provide raw PCM (headerless) stream
            def _ensure_tao_stream_file(wav_path: str) -> Tuple[str, bool]:
                if not using_tao:
                    return wav_path, False
                # Convert WAV to raw PCM (s16le, 44.1kHz, stereo) expected by TAO
                with contextlib.closing(wave.open(wav_path, 'rb')) as wf:
                    n_channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    framerate = wf.getframerate()
                    if not (n_channels == 2 and sampwidth == 2 and framerate == 44100):
                        raise RuntimeError(
                            f"Invalid WAV format for TAO: {n_channels}ch, {sampwidth*8}bit, {framerate}Hz. "
                            "Expected 2ch/16bit/44100Hz."
                        )
                    raw = wf.readframes(wf.getnframes())
                # Defensive: ensure bytes and padding/alignment
                if raw is None:
                    raw = b""
                # Ensure the total byte length is a multiple of audio frame (4 bytes) and sector size (2352)
                if len(raw) % 4 != 0:
                    pad = 4 - (len(raw) % 4)
                    raw += b"\x00" * pad
                # Sector alignment: IMAPI can pad, but some drivers are picky; pre-pad to 2352 boundary
                SECTOR = 2352
                rem = len(raw) % SECTOR
                if rem != 0:
                    raw += b"\x00" * (SECTOR - rem)
                fd, pcm_path = tempfile.mkstemp(prefix='imapi_pcm_', suffix='.pcm')
                os.close(fd)
                with open(pcm_path, 'wb') as f:
                    f.write(raw)
                return pcm_path, True

            # Add tracks (staging phase 50..60)
            stage_start = time.perf_counter()
            for i, p in enumerate(wav_paths):
                if cancel_flag.is_set():
                    raise RuntimeError("Burn canceled")
                if not os.path.exists(p):
                    raise FileNotFoundError(p)
                try:
                    t0 = time.perf_counter()
                    stream_path, is_temp_pcm = _ensure_tao_stream_file(p)
                    if is_temp_pcm:
                        created_pcm_files.append(stream_path)
                    # Prefer memory-backed stream for TAO to avoid any file stream quirks
                    if using_tao:
                        with open(stream_path, 'rb') as f:
                            buf = f.read()
                        stream = _create_stream_on_memory(buf)
                    else:
                        stream = _create_stream_on_file(stream_path)
                    fmt.AddAudioTrack(stream)
                    # Audit: track staged for burning
                    try:
                        session.log_event('track_staged', index=i + 1, wav_path=p)
                    except Exception:
                        pass
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
            if not using_tao:
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
            session.update_status("Burning Completed", progress=100)
        finally:
            # Always disconnect events
            try:
                if conn is not None:
                    conn.disconnect()
            except Exception:
                pass
            # Always release TAO media lock if used
            if using_tao:
                try:
                    rel = getattr(fmt, 'ReleaseMedia', None)
                    if callable(rel):
                        rel()
                except Exception:
                    pass
            # Cleanup temporary PCM files if TAO was used
            for tmp in created_pcm_files:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass


__all__ = [
    'IMAPI2AudioBurner',
    'IMAPIUnavailableError',
]
