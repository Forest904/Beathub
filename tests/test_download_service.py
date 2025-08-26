import os
import subprocess
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `src` can be imported.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.download_service import AudioCoverDownloadService


def test_download_audio_uses_sanitized_title(tmp_path, monkeypatch):
    """Titles with characters like '/' or '?' should produce valid filenames."""
    service = AudioCoverDownloadService()
    item_title = "Weird/Title?"
    sanitized = service._sanitize_filename(item_title)

    captured = {}

    def fake_run(cmd, capture_output, text, check, encoding):
        # capture the path passed to --output
        captured['output'] = cmd[cmd.index('--output') + 1]
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert service.download_audio("https://example.com", tmp_path, item_title)

    output_path = captured['output']
    basename = os.path.basename(output_path)
    assert basename == f"{sanitized}.{{ext}}"
    assert '/' not in basename and '?' not in basename

