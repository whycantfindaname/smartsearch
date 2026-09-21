"""Update selection, trust boundaries, and real streamed-download lifecycle."""
import asyncio
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from unittest.mock import Mock

import httpx
import pytest

from smart_search.i18n import use_language


@pytest.fixture(autouse=True)
def chinese_presentation():
    with use_language("zh"):
        yield

from smart_search import desktop_updates as updates
from smart_search.desktop_backend import Backend


def release(version="0.2.0", arch="x64", digest=True):
    name = f"SmartSearch-{version}-win-{arch}-Setup-unsigned-test.exe"
    asset = {"id": 17, "name": name, "size": 4,
             "browser_download_url": f"{updates.RELEASE_URL}/download/v{version}/{name}"}
    if digest:
        asset["digest"] = "sha256:" + hashlib.sha256(b"test").hexdigest()
    return {"tag_name": f"v{version}", "assets": [asset]}


@pytest.mark.parametrize("remote,current,expected", [("v1.2.3", "1.2.2", True), ("1.2.3", "1.2.3", False),
    ("1.2.2", "1.2.3", False), ("1.3.0-rc.1", "1.2.3", False), ("1.3.0", "dev", False), ("1.2.3", "1.2.3+build", False)])
def test_versions(remote, current, expected):
    assert updates.newer(remote, current) is expected


def test_self_signed_assets_keep_legacy_compatibility_and_reject_ambiguity():
    for architecture in ("x64", "arm64"):
        data = release(arch=architecture)
        assert updates.asset_for(data, "windows", architecture)
        asset = data["assets"][0]
        signed = {**asset, "name": asset["name"].replace("unsigned-test", "signed"),
                  "browser_download_url": asset["browser_download_url"].replace("unsigned-test", "signed")}
        data["assets"] = [signed]
        selected = updates.asset_for(data, "windows", architecture)
        assert selected["name"].endswith("-signed.exe")
        assert selected["signature_verified"] is False  # filename is not local signature verification
        assert updates.asset_for(data, "windows", "arm64" if architecture == "x64" else "x64") is None
        data["assets"].append(asset)
        assert updates.asset_for(data, "windows", architecture) is None


@pytest.mark.asyncio
async def test_release_assets_and_cli_are_independent_and_failed_check_preserves_success(tmp_path, monkeypatch):
    state = {"fail": False, "count": 0}
    def handle(request):
        state["count"] += 1
        if state["fail"]:
            return httpx.Response(429)
        data = [release("0.3.0", arch="arm64"), release(), release("0.1.9")] if request.url.host == "api.github.com" else {"version": "0.3.0"}
        return httpx.Response(200, json=data)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(updates.httpx, "AsyncClient", lambda **_: client)
    monkeypatch.setattr(updates, "platform_target", lambda: ("windows", "x64"))
    manager = updates.Updates(lambda *_: None, directory=tmp_path)
    manager.current_version = "0.1.19"
    manager.check({"external_version": "0.2.5"})
    first_task = manager.check_task
    manager.check({"external_version": "0.2.5"})
    assert manager.check_task is first_task
    await first_task
    assert state["count"] == 2
    assert manager.state["app"]["latest_version"] == "0.2.0"
    assert manager.state["app"]["package_pending"] is True
    assert manager.state["cli"]["latest_version"] == "0.3.0"
    old_success = manager.state["last_success"]
    state["fail"] = True
    monkeypatch.setattr(updates.httpx, "AsyncClient", lambda **_: type(client)(transport=httpx.MockTransport(handle)))
    manager.check({"external_version": "0.2.5"})
    await manager.check_task
    assert manager.state["app"]["latest_version"] == "0.2.0"
    assert manager.state["last_success"] == old_success
    assert manager.state["error"] and manager.state["app"]["error"]
    with pytest.raises(ValueError):
        manager.download()
    assert not manager.state["checking"]


@pytest.mark.asyncio
async def test_checksums_and_untrusted_redirects():
    data = release(digest=False)
    asset = updates.asset_for(data, "windows", "x64")
    assert updates.asset_for(data, "windows", "arm64") is None
    data["assets"].append({"name": "SHA256SUMS.txt", "size": 200,
        "browser_download_url": f"{updates.RELEASE_URL}/download/v0.2.0/SHA256SUMS.txt"})
    seen = []
    def handle(request):
        seen.append(str(request.url))
        if request.url.path.endswith("SHA256SUMS.txt"):
            return httpx.Response(200, text=f"{'a' * 64}  {asset['name']}\n")
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        assert await updates.asset_checksum(client, data, asset) == "a" * 64
        with pytest.raises(ValueError, match="受信任"):
            await updates.asset_response(client, asset["url"])
    assert len(seen) == 2
    for bad in ("https://github.com.evil.test/a", "https://u:p@github.com/a", "http://github.com/a",
                "https://github.com/other/repo/releases/download/a", "https://objects.githubusercontent.com/a"):
        assert not updates.trusted_asset_url(bad)


@pytest.mark.asyncio
async def test_stream_download_retry_cancel_size_hash_and_installer_recheck(tmp_path, monkeypatch):
    content = b"package bytes" * 65536
    source = {"slow": False, "wrong": False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            for offset in range(0, len(content), 16384):
                if source["slow"]:
                    time.sleep(.01)
                try:
                    self.wfile.write((b"x" * 16384) if source["wrong"] else content[offset:offset + 16384])
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(updates, "trusted_asset_url", lambda *a, **k: True)
    monkeypatch.setattr(updates, "platform_target", lambda: ("windows", "x64"))
    manager = updates.Updates(lambda *_: None, directory=tmp_path)
    asset = updates.asset_for(release(), "windows", "x64")
    asset.update(url=f"http://127.0.0.1:{server.server_port}/package", size=len(content), sha256=hashlib.sha256(content).hexdigest())
    manager.state["app"] = {"available": True, "asset": asset}
    try:
        source["slow"] = True
        manager.download()
        first = manager.download_task
        manager.download()
        assert manager.download_task is first
        await asyncio.sleep(.08)
        cancel = Mock(wraps=first.cancel)
        monkeypatch.setattr(first, "cancel", cancel)
        cancellation = asyncio.create_task(manager.cancel_download())
        await asyncio.sleep(0)
        assert manager.state["download"]["status"] == "cancelling"
        await manager.cancel_download()
        manager.download()
        assert manager.download_task is first and cancel.call_count == 1
        await cancellation
        assert manager.state["download"]["status"] == "cancelled"
        assert not list(tmp_path.glob("*.part"))
        source.update(slow=False, wrong=True)
        manager.download()
        await manager.download_task
        assert manager.state["download"]["status"] == "failed"
        with pytest.raises(ValueError):
            await manager.installer()
        source["wrong"] = False
        manager.download()
        await manager.download_task
        assert manager.state["download"]["status"] == "ready"
        assert (await manager.installer())["version"] == "0.2.0"
        (tmp_path / asset["name"]).write_bytes(b"tampered")
        with pytest.raises(ValueError):
            await manager.installer()
        asset["size"] = len(content) - 1
        manager.download()
        await manager.download_task
        assert manager.state["download"]["status"] == "failed"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


@pytest.mark.asyncio
async def test_cancel_before_download_starts_is_terminal_and_retryable(tmp_path):
    events = []
    manager = updates.Updates(lambda _, state: events.append(state["download"]["status"]), directory=tmp_path)
    manager.state["app"] = {"available": True, "asset": updates.asset_for(release(), "windows", "x64")}
    backend = Backend(lambda _: None)
    backend.initialized, backend.directory, backend.updates = True, str(tmp_path), manager
    await backend.handle("updates.download", {})
    result = await backend.handle("updates.cancel", {})
    assert result["download"]["status"] == "cancelled"
    assert events == ["downloading", "cancelling", "cancelled"]
    assert manager.download_task.done() and not list(tmp_path.iterdir())
    manager.download()
    assert manager.state["download"]["status"] == "downloading"
    await manager.cancel_download()


@pytest.mark.asyncio
async def test_auto_check_setting_and_daily_throttle(tmp_path, monkeypatch):
    manager = updates.Updates(lambda *_: None, directory=tmp_path)
    calls = []
    monkeypatch.setattr(manager, "check", lambda info: calls.append(info))
    manager.auto_check({})
    assert not calls  # protocol-only consumers never opt into automatic networking
    manager.enabled = True
    manager.auto_check({})
    assert len(calls) == 1
    manager.state["last_attempt"] = time.time()
    manager.auto_check({})
    assert len(calls) == 1
    manager.state["auto_check"] = False
    manager.save()
    assert updates.Updates(lambda *_: None, directory=tmp_path).state["auto_check"] is False
