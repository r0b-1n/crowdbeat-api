from tests.test_songs import suggest

GUEST_A = {"user-agent": "guest-a"}
GUEST_B = {"user-agent": "guest-b"}


def test_vote_and_count(client, party):
    song = suggest(client, party["code"])
    url = f"/party/{party['code']}/songs/{song['id']}/vote"

    resp = client.post(url, headers=GUEST_A)
    assert resp.status_code == 201
    assert resp.json() == {"song_id": song["id"], "vote_count": 1, "voted": True}

    resp = client.post(url, headers=GUEST_B)
    assert resp.json()["vote_count"] == 2


def test_double_vote_conflict(client, party):
    song = suggest(client, party["code"])
    url = f"/party/{party['code']}/songs/{song['id']}/vote"
    assert client.post(url, headers=GUEST_A).status_code == 201
    assert client.post(url, headers=GUEST_A).status_code == 409


def test_unvote(client, party):
    song = suggest(client, party["code"])
    url = f"/party/{party['code']}/songs/{song['id']}/vote"
    client.post(url, headers=GUEST_A)

    resp = client.request("DELETE", url, headers=GUEST_A)
    assert resp.status_code == 200
    assert resp.json() == {"song_id": song["id"], "vote_count": 0, "voted": False}


def test_unvote_without_vote(client, party):
    song = suggest(client, party["code"])
    url = f"/party/{party['code']}/songs/{song['id']}/vote"
    assert client.request("DELETE", url, headers=GUEST_A).status_code == 404


def test_votes_order_queue(host_client, party):
    code = party["code"]
    first = suggest(host_client, code, title="Song A", track_id="1")
    second = suggest(host_client, code, title="Song B", track_id="2")
    for song in (first, second):
        host_client.patch(f"/party/{code}/songs/{song['id']}", json={"status": "approved"})

    host_client.post(f"/party/{code}/songs/{second['id']}/vote", headers=GUEST_A)
    host_client.post(f"/party/{code}/songs/{second['id']}/vote", headers=GUEST_B)
    host_client.post(f"/party/{code}/songs/{first['id']}/vote", headers=GUEST_A)

    queue = host_client.get(f"/party/{code}/songs").json()
    assert [s["title"] for s in queue] == ["Song B", "Song A"]
    assert [s["vote_count"] for s in queue] == [2, 1]
