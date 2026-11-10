def test_meta_returns_enveloped_camel_case(client) -> None:
    response = client.get("/api/v1/meta")

    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    assert set(body["data"]) == {"name", "version", "env", "serverTime"}
    assert body["data"]["env"] == "test"
