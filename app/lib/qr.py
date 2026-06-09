"""QR code PNG generation for party join links."""

from io import BytesIO

import qrcode


def make_qr_png(data: str) -> bytes:
    img = qrcode.make(data, box_size=10, border=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
