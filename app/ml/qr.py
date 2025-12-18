from pathlib import Path
import qrcode


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def generate_event_qr_png(*, data: str, out_path: Path) -> Path:
    """
    Creates a PNG QR code encoding `data` at out_path.
    """
    ensure_dir(out_path.parent)

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out_path)
    return out_path
