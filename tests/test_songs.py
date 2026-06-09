SONG = {
    "track_id": "123456",
    "title": "Around the World",
    "artist": "Daft Punk",
    "album_art_url": "https://example.com/cover.jpg",
    "duration_ms": 425000,
    "preview_url": "https://example.com/preview.mp3",
    "added_by_name": "Anna",
}


def suggest(client, code, **overrides):
    resp = client.post(f"/party/{code}/songs", json={**SONG, **overrides})
    assert resp.status_code == 201
    return resp.json()


def test_suggest_song_is_pending(client, party):
    song = suggest(client, party["code"])
    assert song["status"] == "pending"
    assert song["vote_count"] == 0
    assert song["youtube_video_id"] is None


def test_approved_list_empty_while_pending(client, party):
    suggest(client, party["code"])
    assert client.get(f"/party/{party['code']}/songs").json() == []


def test_pending_list_requires_host(client, party):
    client.cookies.clear()  # party fixture authenticated this client
    resp = client.get(f"/party/{party['code']}/songs/pending")
    assert resp.status_code == 401


def test_approve_resolves_youtube_id(host_client, party):
    song = suggest(host_client, party["code"])
    resp = host_client.patch(
        f"/party/{party['code']}/songs/{song['id']}", json={"status": "approved"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["youtube_video_id"] == "test-video-id"

    approved = host_client.get(f"/party/{party['code']}/songs").json()
    assert [s["id"] for s in approved] == [song["id"]]


def test_invalid_transition_rejected(host_client, party):
    song = suggest(host_client, party["code"])
    resp = host_client.patch(
        f"/party/{party['code']}/songs/{song['id']}", json={"status": "played"}
    )
    assert resp.status_code == 409


def test_delete_song(host_client, party):
    song = suggest(host_client, party["code"])
    url = f"/party/{party['code']}/songs/{song['id']}"
    assert host_client.delete(url).status_code == 204
    assert host_client.patch(url, json={"status": "approved"}).status_code == 404


def test_played_filter(host_client, party):
    song = suggest(host_client, party["code"])
    url = f"/party/{party['code']}/songs/{song['id']}"
    host_client.patch(url, json={"status": "approved"})
    host_client.patch(url, json={"status": "played"})

    assert host_client.get(f"/party/{party['code']}/songs").json() == []
    played = host_client.get(f"/party/{party['code']}/songs?status=played").json()
    assert [s["id"] for s in played] == [song["id"]]
    resp = host_client.get(f"/party/{party['code']}/songs?status=pending")
    assert resp.status_code == 422  # pending only via the host-only endpoint


def test_suggest_blocked_when_party_ended(host_client, party):
    host_client.delete(f"/party/{party['code']}")
    resp = host_client.post(f"/party/{party['code']}/songs", json=SONG)
    assert resp.status_code == 409
