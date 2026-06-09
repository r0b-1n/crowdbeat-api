import re


def test_create_session_sets_cookie(client):
    resp = client.post("/auth/session", json={"display_name": "DJ"})
    assert resp.status_code == 201
    assert resp.json()["display_name"] == "DJ"
    assert "session_id" in resp.cookies


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_host(host_client):
    resp = host_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "DJ Test"


def test_logout_invalidates_session(host_client):
    assert host_client.post("/auth/logout").status_code == 204
    assert host_client.get("/auth/me").status_code == 401


def test_create_party_requires_auth(client):
    assert client.post("/party", json={"name": "Nope"}).status_code == 401


def test_create_party(party):
    assert party["name"] == "Testparty"
    assert party["status"] == "waiting"
    assert re.fullmatch(r"[A-Z2-9]{3}-[A-Z2-9]{3}", party["code"])


def test_get_party_public(client, party):
    resp = client.get(f"/party/{party['code']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == party["id"]


def test_get_party_unknown_code(client):
    assert client.get("/party/XXX-XXX").status_code == 404


def test_patch_party(host_client, party):
    resp = host_client.patch(f"/party/{party['code']}", json={"status": "active"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_patch_party_foreign_host_forbidden(client, party):
    # New session cookie -> different host than the party owner.
    client.post("/auth/session")
    resp = client.patch(f"/party/{party['code']}", json={"name": "Hijack"})
    assert resp.status_code == 403


def test_delete_ends_party(host_client, party):
    assert host_client.delete(f"/party/{party['code']}").status_code == 204
    assert host_client.get(f"/party/{party['code']}").json()["status"] == "ended"


def test_qr_returns_png(host_client, party):
    resp = host_client.get(f"/party/{party['code']}/qr")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"
