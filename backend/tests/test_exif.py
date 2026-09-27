import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, features

from app import exif
from app.main import app


client = TestClient(app)
API = "/api/v1/exif"
HAS_EXIFTOOL = bool(shutil.which(os.environ.get("EXIFTOOL_PATH", "exiftool")))


def image_bytes(file_format: str) -> bytes:
    image = Image.new("RGB", (3, 2), (34, 123, 201))
    output = io.BytesIO()
    image.save(output, format=file_format)
    return output.getvalue()


def upload(data: bytes, suffix: str = "jpg"):
    return {"image": (f"photo.{suffix}", data, "application/octet-stream")}


def test_catalog_distinguishes_groups_and_rejects_unsafe(monkeypatch):
    xml = """<root>
      <table g0='EXIF' g1='IFD0'><tag name='Shared' type='string' writable='true'/>
        <tag name='Preview' type='binary' writable='true' flags='Binary'/></table>
      <table g0='EXIF' g1='IFD0'><tag name='Shared' g1='ExifIFD' type='string' writable='true'/>
        <tag name='Orientation' type='int16u' writable='true' flags='Unsafe'/></table>
      <table g0='EXIF' g1='Canon'><tag name='Secret' type='string' writable='true'/></table>
    </root>"""
    monkeypatch.setattr(exif, "_run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, xml, ""))
    exif.tag_catalog.cache_clear()
    try:
        entries = exif.tag_catalog()
        assert entries["IFD0:Shared"]["writable"] is True
        assert entries["ExifIFD:Shared"]["writable"] is True
        assert entries["IFD0:Preview"]["writable"] is False
        assert entries["IFD0:Orientation"]["writable"] is False
        assert "Canon:Secret" not in entries
    finally:
        exif.tag_catalog.cache_clear()


def test_exif_http_validation(monkeypatch):
    oversized = client.post(f"{API}/inspect", files=upload(b"x" * (exif.MAX_IMAGE_BYTES + 1)))
    assert oversized.status_code == 413
    assert oversized.json()["code"] == "FILE_TOO_LARGE"
    invalid = client.post(f"{API}/inspect", files=upload(b"not an image"))
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "INVALID_INPUT"
    disguised = client.post(f"{API}/inspect", files=upload(image_bytes("PNG"), "jpg"))
    assert disguised.status_code == 400
    malformed = client.post(f"{API}/edit", files=upload(b"\xff\xd8\xff"), data={"changes": "not-json"})
    assert malformed.status_code == 422
    monkeypatch.setattr(exif, "tag_catalog", lambda: {"IFD0:Make": {"writable": False}})
    readonly = client.post(
        f"{API}/edit", files=upload(b"\xff\xd8\xff"),
        data={"changes": json.dumps([{"key": "IFD0:Make", "action": "set", "value": "x"}])},
    )
    assert readonly.status_code == 400
    assert "IFD0:Make" in readonly.json()["message"]


@pytest.mark.skipif(not HAS_EXIFTOOL, reason="ExifTool is not installed")
@pytest.mark.parametrize("file_format,suffix", [("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp")])
def test_exif_roundtrip_and_pixels(file_format, suffix):
    if file_format == "WEBP" and not features.check("webp"):
        pytest.skip("Pillow was built without WebP")
    source = image_bytes(file_format)
    first = client.post(f"{API}/inspect", files=upload(source, suffix))
    assert first.status_code == 200, first.text
    assert first.json()["format"] == file_format
    assert first.json()["tags"] == []
    catalog = client.get(f"{API}/tags?q=Make")
    assert catalog.status_code == 200
    assert any(tag["key"] == "IFD0:Make" for tag in catalog.json()["tags"])

    changes = [
        {"key": "IFD0:Make", "action": "set", "value": "Superbox"},
        {"key": "ExifIFD:DateTimeOriginal", "action": "set", "value": "2026:09:27 10:20:30"},
    ]
    edited = client.post(f"{API}/edit", files=upload(source, suffix), data={"changes": json.dumps(changes)})
    assert edited.status_code == 200, edited.text
    assert edited.headers["content-type"] == f"image/{'jpeg' if file_format == 'JPEG' else suffix}"
    assert "attachment" in edited.headers["content-disposition"]
    with Image.open(io.BytesIO(source)) as original, Image.open(io.BytesIO(edited.content)) as output:
        assert original.size == output.size
        assert original.tobytes() == output.tobytes()
    inspected = client.post(f"{API}/inspect", files=upload(edited.content, suffix))
    make = next(tag for tag in inspected.json()["tags"] if tag["key"] == "IFD0:Make")
    assert make["value"] == "Superbox"
    assert any(tag["key"] == "ExifIFD:DateTimeOriginal" and tag["value"] == "2026:09:27 10:20:30" for tag in inspected.json()["tags"])

    modified = client.post(
        f"{API}/edit", files=upload(edited.content, suffix),
        data={"changes": json.dumps([{"key": "IFD0:Make", "action": "set", "value": "Changed"}])},
    )
    assert modified.status_code == 200, modified.text
    assert any(tag["key"] == "IFD0:Make" and tag["value"] == "Changed" for tag in client.post(f"{API}/inspect", files=upload(modified.content, suffix)).json()["tags"])

    removed = client.post(
        f"{API}/edit", files=upload(modified.content, suffix),
        data={"changes": json.dumps([{"key": "IFD0:Make", "action": "delete"}, {"key": "ExifIFD:DateTimeOriginal", "action": "delete"}])},
    )
    assert removed.status_code == 200, removed.text
    after = client.post(f"{API}/inspect", files=upload(removed.content, suffix)).json()
    assert not any(tag["key"] == "IFD0:Make" for tag in after["tags"])
    assert not any(tag["key"] == "ExifIFD:DateTimeOriginal" for tag in after["tags"])


@pytest.mark.skipif(not HAS_EXIFTOOL, reason="ExifTool is not installed")
def test_exif_invalid_value_and_other_metadata_survive():
    source = image_bytes("JPEG")
    bad = client.post(
        f"{API}/edit", files=upload(source),
        data={"changes": json.dumps([{"key": "GPS:GPSLatitude", "action": "set", "value": "not-a-coordinate"}])},
    )
    assert bad.status_code == 400
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "image.jpg"
        path.write_bytes(source)
        result = exif._run("-overwrite_original", "-XMP-dc:Title=Keep this", "--", str(path))
        assert result.returncode == 0
        edited = client.post(
            f"{API}/edit", files=upload(path.read_bytes()),
            data={"changes": json.dumps([{"key": "ExifIFD:UserComment", "action": "set", "value": "Hello EXIF"}])},
        )
        assert edited.status_code == 200, edited.text
        path.write_bytes(edited.content)
        assert exif._run("-s3", "-XMP-dc:Title", "--", str(path)).stdout.strip() == "Keep this"
        inspected = client.post(f"{API}/inspect", files=upload(edited.content)).json()
        assert any(tag["key"] == "ExifIFD:UserComment" and tag["value"] == "Hello EXIF" for tag in inspected["tags"])
