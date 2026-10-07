from io import BytesIO

import pytest
from PIL import Image

from app.models import Event, News
from app.services import content_images


def png():
    buffer = BytesIO()
    Image.new("RGB", (3, 3), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def isolated_uploads(monkeypatch, tmp_path):
    monkeypatch.setattr(content_images, "UPLOAD_ROOT", tmp_path)


def form(category):
    if category == "events":
        return {"title": "Image event", "description": "Details", "start_time": "2027-10-01T12:00", "capacity": "10"}
    return {"title": "Image news", "content": "Details"}


@pytest.mark.parametrize("category,model", [("events", Event), ("news", News)])
def test_create_online_image(admin_client, db, category, model):
    data = dict(form(category), image_url="https://example.com/poster.png")
    response = admin_client.post(f"/admin/{category}/create", data=data, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(model).one().image_url == data["image_url"]


@pytest.mark.parametrize("category,model", [("events", Event), ("news", News)])
def test_uploaded_file_precedes_url_and_edit_preserves_it(admin_client, db, category, model):
    data = dict(form(category), image_url="javascript:invalid")
    response = admin_client.post(f"/admin/{category}/create", data=data,
        files={"image_file": ("../../poster.html", png(), "text/html")}, follow_redirects=False)
    assert response.status_code == 303
    item = db.query(model).one()
    saved = item.image_url
    assert saved.startswith(f"/static/uploads/{category}/") and saved.endswith(".png")
    assert (content_images.UPLOAD_ROOT / category / saved.rsplit("/", 1)[1]).read_bytes() == png()
    response = admin_client.post(f"/admin/{category}/{item.id}/edit", data=form(category), follow_redirects=False)
    assert response.status_code == 303
    db.refresh(item)
    assert item.image_url == saved
    response = admin_client.post(f"/admin/{category}/{item.id}/edit", data=form(category),
        files={"image_file": ("new.png", png(), "image/png")}, follow_redirects=False)
    assert response.status_code == 303
    db.refresh(item)
    assert item.image_url != saved


@pytest.mark.parametrize("category,model", [("events", Event), ("news", News)])
@pytest.mark.parametrize("payload", [b"<script>fake image</script>", b"x" * (content_images.MAX_IMAGE_BYTES + 1)], ids=["not-image", "oversized"])
def test_invalid_file_does_not_create_record(admin_client, db, category, model, payload):
    response = admin_client.post(f"/admin/{category}/create", data=form(category),
        files={"image_file": ("fake.png", payload, "image/png")}, follow_redirects=False)
    assert response.status_code == 400
    assert db.query(model).count() == 0
    assert not list(content_images.UPLOAD_ROOT.rglob("*"))


@pytest.mark.parametrize("category,model", [("events", Event), ("news", News)])
def test_rejected_edit_preserves_record(admin_client, db, category, model):
    admin_client.post(f"/admin/{category}/create", data=form(category), follow_redirects=False)
    item = db.query(model).one()
    response = admin_client.post(f"/admin/{category}/{item.id}/edit",
        data=dict(form(category), title="Changed", image_url="javascript:alert(1)"), follow_redirects=False)
    assert response.status_code == 400
    db.refresh(item)
    assert item.title == form(category)["title"]


@pytest.mark.parametrize("value", ["javascript:alert(1)", "//evil.test/photo", "https://user:pass@example.com/a", "/static/../secret", "https://example.com/\nphoto"])
def test_invalid_url(value):
    with pytest.raises(ValueError):
        content_images.validate_image_url(value)


@pytest.mark.parametrize("path", ["/admin/events", "/admin/news/create"])
def test_forms_offer_both_sources(admin_client, path):
    response = admin_client.get(path)
    assert response.status_code == 200
    assert 'enctype="multipart/form-data"' in response.text
    assert 'name="image_file"' in response.text
    assert 'name="image_url"' in response.text
