"""Explicit desktop package updates; no shell, service, or implicit installation."""
from __future__ import annotations
from .i18n import tr

import asyncio
import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import time
from urllib.parse import urlsplit

import httpx

REPOSITORY = "konbakuyomu/smartsearch"
RELEASE_URL = f"https://github.com/{REPOSITORY}/releases"
RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=100"
NPM_URL = "https://registry.npmjs.org/@konbakuyomu%2fsmart-search/latest"
PACKAGE = "@konbakuyomu/smart-search"
MAX_PACKAGE_BYTES = 1024 * 1024 * 1024


def stable_version(value):
    match = re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\+[0-9A-Za-z.-]+)?", str(value))
    return tuple(map(int, match.groups())) if match else None


def newer(remote, current):
    a, b = stable_version(remote), stable_version(current)
    return a is not None and b is not None and a > b


def platform_target():
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64" if machine in {"amd64", "x86_64"} else "unsupported"
    system = "windows" if os.name == "nt" else "macos" if platform.system() == "Darwin" else "unsupported"
    return system, "x86_64" if system == "macos" and arch == "x64" else arch


def cache_directory():
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "SmartSearch/updates"
    return Path.home() / "Library/Caches/SmartSearch/updates"


def trusted_asset_url(url, *, redirected=False):
    parsed = urlsplit(str(url))
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443} or parsed.fragment:
        return False
    if parsed.hostname == "github.com":
        return parsed.path.startswith(f"/{REPOSITORY}/releases/download/")
    return redirected and parsed.hostname in {"release-assets.githubusercontent.com", "objects.githubusercontent.com"}


async def asset_response(client, url):
    """Validate every redirect before making the next request (including host)."""
    for hop in range(6):
        if not trusted_asset_url(url, redirected=hop > 0):
            raise ValueError(tr('安装包地址不是受信任的官方发行地址。'))
        response = await client.send(client.build_request("GET", url), stream=True)
        if response.is_redirect:
            location = response.headers.get("location", "")
            next_url = str(response.url.join(location))
            await response.aclose()
            url = next_url
            continue
        response.raise_for_status()
        return response
    raise ValueError(tr('安装包下载跳转次数过多。'))


def asset_for(release, system, arch):
    version = str(release.get("tag_name", "")).removeprefix("v")
    suffix = "exe" if system == "windows" else "dmg"
    target = f"win-{arch}-Setup" if system == "windows" else f"macos-{arch}"
    pattern = re.compile(rf"SmartSearch-{re.escape(version)}-{target}-(?:unsigned-test|unsigned|signed)\.{suffix}", re.I)
    matches = [a for a in release.get("assets", []) if pattern.fullmatch(a.get("name", ""))]
    if len(matches) != 1:
        return None
    asset = matches[0]
    size = asset.get("size", 0)
    if type(size) is not int or not 0 < size <= MAX_PACKAGE_BYTES or not trusted_asset_url(asset.get("browser_download_url", "")):
        return None
    return {"version": version, "id": asset.get("id"), "name": asset["name"], "size": size,
            "url": asset["browser_download_url"], "digest": asset.get("digest", ""),
            "platform": system, "architecture": arch, "signature_verified": False}


async def asset_checksum(client, release, asset):
    digest = asset.get("digest") or ""
    if re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        return digest[7:].lower()
    sums = next((a for a in release.get("assets", []) if a.get("name") == "SHA256SUMS.txt"), None)
    if not sums or not 0 < sums.get("size", 0) <= 65536:
        return None
    response = await asset_response(client, sums.get("browser_download_url", ""))
    try:
        content = bytearray()
        async for chunk in response.aiter_bytes():
            content.extend(chunk)
            if len(content) > 65536:
                raise ValueError(tr('校验清单过大。'))
    finally:
        await response.aclose()
    for line in content.decode("utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line.strip())
        if match and match[2] == asset["name"]:
            return match[1].lower()
    return None


def verified_file(path, asset):
    if not path.is_file() or path.stat().st_size != asset["size"]:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == asset["sha256"]


def check_error(error):
    if isinstance(error, httpx.TimeoutException):
        return "timeout", tr('请求超时，请稍后重试。')
    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code in {403, 429}:
        return "rate_limited", tr('发行服务拒绝请求或限流，请稍后重试。')
    if isinstance(error, httpx.HTTPError):
        return "network_error", tr('无法连接发行服务，请检查网络后重试。')
    return "invalid_metadata", tr('发行信息不完整或无效，请查看官方发行页面。')


class Updates:
    def __init__(self, emit, *, directory=None):
        self.emit = emit
        self.directory = Path(directory) if directory else cache_directory()
        self.current_version = ""
        self.enabled = False
        self.check_task = self.download_task = self.cli_task = None
        self.state = {"auto_check": True, "last_attempt": 0, "last_success": 0, "checking": False,
                      "error": "", "app": {}, "cli": {}, "download": {"status": "idle"},
                      "cli_update": {"status": "idle"}, "release_url": RELEASE_URL}
        try:
            saved = json.loads((self.directory / "state.json").read_text(encoding="utf-8"))
            if type(saved.get("auto_check")) is bool:
                self.state["auto_check"] = saved["auto_check"]
            for key in ("last_attempt", "last_success"):
                if type(saved.get(key)) in {int, float} and 0 <= saved[key] <= time.time():
                    self.state[key] = saved[key]
            for key in ("app", "cli"):
                if isinstance(saved.get(key), dict):
                    self.state[key] = {k: v for k, v in saved[key].items()
                                       if k in {"latest_version", "latest_release", "checked_at", "package_pending"}}
                    self.state[key].update(available=False, error=tr('此前检查结果，需重新检查后才能更新。'), cached=True)
        except (OSError, ValueError, TypeError):
            pass

    def changed(self):
        self.emit("updates", self.state)

    def save(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        data = {k: self.state[k] for k in ("auto_check", "last_attempt", "last_success", "app", "cli")}
        temporary = self.directory / "state.json.tmp"
        temporary.write_text(json.dumps(data), encoding="utf-8")
        temporary.replace(self.directory / "state.json")

    def auto_check(self, cli_info):
        if self.enabled and self.state["auto_check"] and time.time() - self.state["last_attempt"] >= 86400:
            self.check(cli_info)

    def check(self, cli_info):
        if self.check_task and not self.check_task.done():
            return self.state
        self.state.update(checking=True, last_attempt=time.time(), error="")
        self.save()
        self.changed()
        self.check_task = asyncio.create_task(self._check(dict(cli_info)))
        return self.state

    async def _check(self, cli_info):
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
                responses = await asyncio.gather(client.get(RELEASE_API), client.get(NPM_URL), return_exceptions=True)
                app_response, cli_response = responses
                errors = []
                try:
                    if isinstance(app_response, Exception):
                        raise app_response
                    app_response.raise_for_status()
                    releases = app_response.json()
                    releases = sorted((r for r in releases if not r.get("draft") and not r.get("prerelease") and stable_version(r.get("tag_name"))),
                                      key=lambda r: stable_version(r["tag_name"]), reverse=True)
                    chosen = None
                    for release in releases:
                        asset = asset_for(release, *platform_target())
                        if asset:
                            checksum = await asset_checksum(client, release, asset)
                            if checksum:
                                chosen = {**asset, "sha256": checksum}
                                break
                    latest = releases[0]["tag_name"] if releases else ""
                    self.state["app"] = {"current_version": self.current_version, "latest_version": chosen["version"] if chosen else "",
                                         "latest_release": latest, "available": bool(chosen and newer(chosen["version"], self.current_version)),
                                         "package_pending": bool(latest and (not chosen or newer(latest, chosen["version"]))),
                                         "asset": chosen, "checked_at": time.time(), "error": "",
                                         "version_known": stable_version(self.current_version) is not None}
                except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as error:
                    error_type, message = check_error(error)
                    errors.append(tr('App 检查失败：') + message)
                    self.state["app"] = {**self.state["app"], "error": errors[-1], "error_type": error_type}
                try:
                    if isinstance(cli_response, Exception):
                        raise cli_response
                    cli_response.raise_for_status()
                    latest = cli_response.json()["version"]
                    if stable_version(latest) is None:
                        raise ValueError(tr('invalid stable version'))
                    self.state["cli"] = {"current_version": cli_info.get("external_version"), "latest_version": latest,
                                         "available": newer(latest, cli_info.get("external_version")), "checked_at": time.time(), "error": ""}
                    if cli_info.get("can_update"):
                        from .desktop_cli import update_command
                        command = update_command(cli_info, latest)
                        self.state["cli"]["command"] = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
                except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
                    error_type, message = check_error(error)
                    errors.append(tr('CLI 检查失败：') + message)
                    self.state["cli"] = {**self.state["cli"], "error": errors[-1], "error_type": error_type}
                self.state["error"] = "\n".join(errors)
                if not errors:
                    self.state["last_success"] = time.time()
        finally:
            self.state["checking"] = False
            self.save()
            self.changed()

    def download(self):
        if self.state["download"]["status"] == "cancelling" or self.download_task and not self.download_task.done():
            return self.state
        app = self.state["app"]
        if not app.get("available") or not app.get("asset") or app.get("error"):
            raise ValueError(tr('请先成功检查并选择与当前平台匹配的新版安装包。'))
        asset = dict(app["asset"])
        self.state["download"] = {"status": "downloading", "asset": asset, "received": 0, "total": asset["size"], "error": ""}
        self.changed()
        self.download_task = asyncio.create_task(self._download(asset))
        return self.state

    async def cancel_download(self):
        task = self.download_task
        status = self.state["download"]
        if task and not task.done() and status["status"] == "downloading":
            status["status"] = "cancelling"
            self.changed()
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            # A task cancelled before its first step never enters _download's cleanup.
            if status["status"] == "cancelling":
                status.update(status="cancelled", error=tr('下载已取消，可重新下载。'))
                self.changed()
        return self.state

    async def _download(self, asset):
        target = self.directory / asset["name"]
        partial = target.with_suffix(target.suffix + ".part")
        status = self.state["download"]
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            if not await asyncio.to_thread(verified_file, target, asset):
                digest = hashlib.sha256()
                last_notice = 0
                async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
                    response = await asset_response(client, asset["url"])
                    try:
                        started = time.monotonic()
                        with partial.open("wb") as stream:
                            async for chunk in response.aiter_bytes(65536):
                                if time.monotonic() - started > 1800:
                                    raise ValueError(tr('下载超过 30 分钟，请重试。'))
                                status["received"] += len(chunk)
                                if status["received"] > asset["size"]:
                                    raise ValueError(tr('安装包大小与发布记录不符。'))
                                stream.write(chunk)
                                digest.update(chunk)
                                if time.monotonic() - last_notice >= .2:
                                    self.changed()
                                    last_notice = time.monotonic()
                        if status["received"] != asset["size"] or digest.hexdigest() != asset["sha256"]:
                            raise ValueError(tr('安装包大小或 SHA256 校验失败，请重试。'))
                        partial.replace(target)
                    finally:
                        await response.aclose()
            status.update(status="ready", received=asset["size"], path=str(target))
        except asyncio.CancelledError:
            status.update(status="cancelled", error=tr('下载已取消，可重新下载。'))
        except (httpx.HTTPError, OSError, ValueError):
            status.update(status="failed", error=tr('下载失败或完整性校验不符；未执行安装，可重试。'))
        finally:
            with contextlib.suppress(OSError):
                partial.unlink(missing_ok=True)
            self.changed()

    async def installer(self):
        state = self.state["download"]
        asset = state.get("asset", {})
        path = self.directory / asset.get("name", "missing")
        if state.get("status") != "ready" or (asset.get("platform"), asset.get("architecture")) != platform_target() or not await asyncio.to_thread(verified_file, path, asset):
            raise ValueError(tr('安装包尚未就绪或校验已失效，请重新下载。'))
        return {"ok": True, "path": str(path.resolve()), "version": asset["version"], "signature_verified": False}

    async def close(self):
        for task in (self.check_task, self.download_task):
            if task and not task.done():
                task.cancel()
        await asyncio.gather(*(task for task in (self.check_task, self.download_task, self.cli_task) if task), return_exceptions=True)
