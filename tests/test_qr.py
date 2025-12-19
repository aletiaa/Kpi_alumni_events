from pathlib import Path
from app.ml.qr import generate_event_qr_png

def test_generate_qr_creates_file(tmp_path):
    out = tmp_path / "qrs" / "event_1.png"
    result = generate_event_qr_png(data="https://example.com/event/1", out_path=out)
    assert result.exists()
    assert result.suffix.lower() == ".png"
    assert result.stat().st_size > 0
