def assert_dict_contains(actual, expected):
    assert expected.items() <= actual.items()


def create_profile_layer_binding(client):
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()
    layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Layer"},
    ).json()
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 60},
            "action": {
                "type": "command",
                "label": "Run command",
                "command": "echo run",
            },
        },
    ).json()
    return profile, layer, binding


def patch_executor(monkeypatch, result):
    calls = []

    async def fake_execute(command):
        calls.append(command)
        return dict(result)

    import backend.api.actions as actions_api

    monkeypatch.setattr(actions_api, "safe_execute_command", fake_execute)
    return calls


def test_action_test_creates_run_with_v2_linkage(client, monkeypatch):
    profile, layer, binding = create_profile_layer_binding(client)
    calls = patch_executor(
        monkeypatch,
        {
            "ok": True,
            "pid": 123,
            "stdout_preview": "hello",
            "stderr_preview": "",
            "exit_code": 0,
        },
    )

    response = client.post(f"/api/actions/{binding['action_id']}/test")

    assert response.status_code == 200
    body = response.json()
    assert calls == ["echo run"]
    assert body["run_id"] >= 1

    runs = client.get("/api/runs").json()
    assert len(runs) == 1
    assert_dict_contains(runs[0], {
        "id": body["run_id"],
        "action_id": binding["action_id"],
        "binding_id": binding["id"],
        "profile_id": profile["id"],
        "layer_id": layer["id"],
        "trigger_snapshot_json": "{}",
        "action_summary": "echo run",
        "status": "success",
        "exit_code": 0,
        "stdout_preview": "hello",
        "stderr_preview": "",
        "error_message": "",
    })
    assert runs[0]["started_at"]
    assert runs[0]["finished_at"]
    assert runs[0]["duration_ms"] >= 0

    detail = client.get(f"/api/runs/{body['run_id']}").json()
    assert detail == runs[0]


def test_dry_run_does_not_create_run(client, monkeypatch):
    _, _, binding = create_profile_layer_binding(client)
    calls = patch_executor(monkeypatch, {"ok": True})

    response = client.post(f"/api/actions/{binding['action_id']}/dry_run")

    assert response.status_code == 200
    assert calls == []
    assert client.get("/api/runs").json() == []


def test_failed_action_test_creates_error_run(client, monkeypatch):
    _, _, binding = create_profile_layer_binding(client)
    patch_executor(
        monkeypatch,
        {
            "ok": False,
            "error": "Command 'missing' not found in PATH",
            "stderr": "missing",
        },
    )

    response = client.post(f"/api/actions/{binding['action_id']}/test")

    assert response.status_code == 200
    run = client.get(f"/api/runs/{response.json()['run_id']}").json()
    assert_dict_contains(run, {
        "action_id": binding["action_id"],
        "binding_id": binding["id"],
        "status": "error",
        "exit_code": None,
        "stderr_preview": "missing",
        "error_message": "Command 'missing' not found in PATH",
    })


def test_run_output_previews_are_truncated(client, monkeypatch):
    _, _, binding = create_profile_layer_binding(client)
    patch_executor(
        monkeypatch,
        {
            "ok": True,
            "exit_code": 0,
            "stdout": "x" * 1200,
            "stderr": "y" * 1200,
        },
    )

    response = client.post(f"/api/actions/{binding['action_id']}/test")

    assert response.status_code == 200
    run = client.get(f"/api/runs/{response.json()['run_id']}").json()
    assert len(run["stdout_preview"]) == 1000
    assert len(run["stderr_preview"]) == 1000
    assert run["stdout_preview"] == "x" * 1000
    assert run["stderr_preview"] == "y" * 1000


def test_clear_runs_deletes_all_runs(client, monkeypatch):
    _, _, binding = create_profile_layer_binding(client)
    patch_executor(monkeypatch, {"ok": True, "exit_code": 0})
    client.post(f"/api/actions/{binding['action_id']}/test")
    client.post(f"/api/actions/{binding['action_id']}/test")
    assert len(client.get("/api/runs").json()) == 2

    response = client.delete("/api/runs")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["deleted"] == 2
    assert client.get("/api/runs").json() == []


def test_clear_runs_does_not_affect_bindings_or_actions(client, monkeypatch):
    profile, layer, binding = create_profile_layer_binding(client)
    patch_executor(monkeypatch, {"ok": True, "exit_code": 0})
    client.post(f"/api/actions/{binding['action_id']}/test")

    client.delete("/api/runs")

    # Binding and action still exist
    bindings = client.get(f"/api/layers/{layer['id']}/bindings").json()
    assert len(bindings) == 1
    assert bindings[0]["id"] == binding["id"]
    assert bindings[0]["action_id"] == binding["action_id"]


def test_clear_runs_on_empty_history_returns_zero(client):
    response = client.delete("/api/runs")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "deleted": 0}
