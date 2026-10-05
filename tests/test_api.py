import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("PCLINK_HOME", str(tmp_path / "home"))
    from pclink.app import create_app
    from pclink.config import load_config

    root = tmp_path / "root"
    root.mkdir()
    cfg = load_config()
    cfg.allowed_roots = [str(root)]
    client = TestClient(create_app(cfg))
    return client, cfg, root


def login(client, cfg):
    assert client.post("/api/login", json={"token": cfg.token}).status_code == 200


def test_requires_login(env):
    client, cfg, root = env
    assert client.get("/api/fs/roots").status_code == 401
    assert client.get("/").status_code == 200  # 웹앱은 공개
    login(client, cfg)
    assert client.get("/api/fs/roots").json()["roots"] == [str(root.resolve())]


def test_bruteforce_lock(env):
    client, cfg, _ = env
    for _ in range(5):
        assert client.post("/api/login", json={"token": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"token": cfg.token}).status_code == 429


def test_file_lifecycle(env):
    client, cfg, root = env
    login(client, cfg)
    r = str(root)
    assert client.post("/api/fs/mkdir", json={"path": f"{r}/a"}).status_code == 200
    up = client.post("/api/fs/upload", data={"dir": f"{r}/a"}, files=[("files", ("메모.txt", "안녕".encode()))])
    assert up.status_code == 200
    f = up.json()["saved"][0]
    assert Path(f).name == "메모.txt"
    assert client.get("/api/fs/read", params={"path": f}).json()["content"] == "안녕"
    assert client.post("/api/fs/write", json={"path": f, "content": "수정"}).status_code == 200
    assert client.get("/api/fs/download", params={"path": f}).content.decode() == "수정"
    assert client.post("/api/fs/rename", json={"path": f, "new_name": "b.txt"}).status_code == 200
    client.post("/api/fs/mkdir", json={"path": f"{r}/c"})
    assert client.post("/api/fs/copy", json={"paths": [f"{r}/a/b.txt"], "dest": f"{r}/c"}).status_code == 200
    assert client.post("/api/fs/copy", json={"paths": [f"{r}/a/b.txt"], "dest": f"{r}/c"}).json()["done"][0].endswith("b (1).txt")
    assert client.post("/api/fs/move", json={"paths": [f"{r}/c"], "dest": f"{r}/a"}).status_code == 200
    names = [i["name"] for i in client.get("/api/fs/list", params={"path": f"{r}/a"}).json()["items"]]
    assert names == ["c", "b.txt"]
    assert len(client.get("/api/fs/search", params={"path": r, "q": "b"}).json()["items"]) == 3
    assert client.get("/api/fs/download", params={"path": f"{r}/a"}).headers["content-type"] == "application/zip"
    assert client.post("/api/fs/delete", json={"paths": [f"{r}/a/c"]}).status_code == 200
    assert not (root / "a" / "c").exists()


def test_path_restrictions(env, tmp_path):
    client, cfg, root = env
    login(client, cfg)
    outside = tmp_path / "secret.txt"
    outside.write_text("x")
    assert client.get("/api/fs/read", params={"path": str(outside)}).status_code == 403
    assert client.get("/api/fs/read", params={"path": f"{root}/../secret.txt"}).status_code == 403
    assert client.get("/api/fs/list", params={"path": "relative"}).status_code == 400
    assert client.post("/api/fs/rename", json={"path": f"{root}", "new_name": "../x"}).status_code == 400
    # 업로드 파일명으로 상위 경로 탈출 불가
    up = client.post("/api/fs/upload", data={"dir": str(root)}, files=[("files", ("../../evil.txt", b"x"))])
    assert Path(up.json()["saved"][0]).parent == root.resolve()
    # 폴더를 자기 자신 안으로 이동 불가
    client.post("/api/fs/mkdir", json={"path": f"{root}/d"})
    assert client.post("/api/fs/move", json={"paths": [f"{root}/d"], "dest": f"{root}/d"}).status_code == 400


@pytest.mark.skipif(os.name == "nt", reason="심볼릭 링크 권한")
def test_symlink_delete_keeps_target(env, tmp_path):
    client, cfg, root = env
    login(client, cfg)
    target = root / "real.txt"
    target.write_text("keep")
    (root / "link.txt").symlink_to(target)
    assert client.post("/api/fs/delete", json={"paths": [f"{root}/link.txt"], "permanent": True}).status_code == 200
    assert target.read_text() == "keep"
    # 허용 범위 밖을 가리키는 링크는 읽을 수 없음
    (tmp_path / "out.txt").write_text("s")
    (root / "out-link.txt").symlink_to(tmp_path / "out.txt")
    assert client.get("/api/fs/read", params={"path": f"{root}/out-link.txt"}).status_code == 403


def test_terminal_disabled_and_power_confirm(env):
    client, cfg, _ = env
    login(client, cfg)
    assert client.post("/api/terminal/run", json={"command": "echo hi"}).status_code == 403
    assert client.post("/api/system/power", json={"action": "shutdown"}).status_code == 400


def test_system_and_processes(env):
    client, cfg, _ = env
    login(client, cfg)
    info = client.get("/api/system/info").json()
    assert "cpu_percent" in info and "memory" in info
    assert any(p["pid"] == os.getpid() for p in client.get("/api/processes").json()["items"])
    assert client.post("/api/processes/kill", json={"pid": os.getpid()}).status_code == 400
    assert client.get("/api/apps").status_code == 200
    assert client.post("/api/apps/launch", json={"id": "nope"}).status_code == 404


def test_audit_log(env):
    client, cfg, root = env
    login(client, cfg)
    client.post("/api/fs/mkdir", json={"path": f"{root}/z"})
    log = (Path(os.environ["PCLINK_HOME"]) / "audit.log").read_text(encoding="utf-8")
    assert '"action": "mkdir"' in log and '"action": "login"' in log
