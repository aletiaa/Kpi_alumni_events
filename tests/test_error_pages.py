from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.deps import require_identity
from app.errors import handle_http_error, handle_server_error


@pytest.mark.parametrize("url,status", [("/admin/kpi-import", 401), ("/does-not-exist", 404), ("/surveys/not-an-id", 422)])
def test_browser_errors_are_html(client, url, status):
    response = client.get(url, headers={"Accept": "text/html"})
    assert response.status_code == status
    assert response.headers['content-type'].startswith('text/html')
    assert f'data-no-translate>{status}</div>' in response.text
    assert 'id="error-title"' in response.text
    assert 'href="/"' in response.text
    assert response.headers['cache-control'] == 'no-store'
    if status == 401:
        assert 'href="/login"' in response.text


def test_forbidden_page_and_json_contract(client):
    client.app.dependency_overrides[require_identity] = lambda: SimpleNamespace(role="alumni")
    response = client.get('/admin/kpi-import', headers={"Accept": "text/html"})
    assert response.status_code == 403 and 'error_403_title' in response.text
    response = client.get('/admin/kpi-import', headers={"Accept": "application/json"})
    assert response.status_code == 403 and 'detail' in response.json()


@pytest.mark.parametrize('accept', ['*/*', 'application/json', 'text/html;q=0, application/json', 'text/html;q=0.5,application/json;q=1'])
def test_json_clients_keep_json(client, accept):
    response = client.get('/does-not-exist', headers={"Accept": accept})
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_api_paths_keep_json_even_with_browser_accept(client):
    response = client.get('/api/missing', headers={"Accept": "text/html"})
    assert response.status_code == 404 and 'detail' in response.json()
    response = client.post('/assistant/query', json={}, headers={"Accept": "text/html"})
    assert response.headers['content-type'].startswith('application/json')


def test_error_handlers_hide_internal_details_and_preserve_headers(client):
    import asyncio

    request = Request({"type": "http", "method": "GET", "path": "/broken", "headers": [(b'accept', b'text/html')], "app": client.app, "query_string": b''})
    response = asyncio.run(handle_server_error(request, RuntimeError('private connection string')))
    assert response.status_code == 500
    assert b'private connection string' not in response.body
    assert b'error_500_title' in response.body
    response = asyncio.run(handle_http_error(request, HTTPException(429, 'private detail', headers={'Retry-After': '60'})))
    assert response.status_code == 429 and response.headers['retry-after'] == '60'
    assert b'private detail' not in response.body
