import base64
import io
import os
import re
import stat
import tarfile
import time
from typing import List

import docker
import requests
from docker.errors import APIError, DockerException, ImageNotFound

from . import config

SAFE_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")

TURTLE_STUB = """# Minimal turtle-like module that writes turtle.svg on exit.
import atexit
import math

WIDTH = 500
HEIGHT = 500

_state = {
    "x": 0.0,
    "y": 0.0,
    "heading": 0.0,
    "pen": True,
    "color": "#6aa6ff",
    "width": 2,
}
_paths = []


def _to_svg(x, y):
    return x + WIDTH / 2, HEIGHT / 2 - y


def _line_to(x, y):
    if _state["pen"]:
        _paths.append((_state["x"], _state["y"], x, y, _state["color"], _state["width"]))
    _state["x"], _state["y"] = x, y


def forward(dist):
    radians = math.radians(_state["heading"])
    x = _state["x"] + math.cos(radians) * dist
    y = _state["y"] + math.sin(radians) * dist
    _line_to(x, y)


def backward(dist):
    forward(-dist)


def left(angle):
    _state["heading"] = (_state["heading"] + angle) % 360


def right(angle):
    _state["heading"] = (_state["heading"] - angle) % 360


def penup():
    _state["pen"] = False


def pendown():
    _state["pen"] = True


def goto(x, y):
    _line_to(float(x), float(y))


def setheading(angle):
    _state["heading"] = float(angle) % 360


def color(value):
    _state["color"] = str(value)


def pensize(value):
    _state["width"] = max(1, int(value))


def circle(radius, steps=36):
    step = 360 / steps
    step_len = (2 * math.pi * radius) / steps
    for _ in range(steps):
        forward(step_len)
        left(step)


def write_svg(path="turtle.svg"):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" ',
        f'viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="#0b0f14"/>',
    ]
    for x1, y1, x2, y2, color, width in _paths:
        sx1, sy1 = _to_svg(x1, y1)
        sx2, sy2 = _to_svg(x2, y2)
        parts.append(
            f'<line x1="{sx1}" y1="{sy1}" x2="{sx2}" y2="{sy2}" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" />'
        )
    parts.append("</svg>")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\\n".join(parts))


def done():
    write_svg()


class Turtle:
    def forward(self, dist): forward(dist)
    def backward(self, dist): backward(dist)
    def left(self, angle): left(angle)
    def right(self, angle): right(angle)
    def penup(self): penup()
    def pendown(self): pendown()
    def goto(self, x, y): goto(x, y)
    def setheading(self, angle): setheading(angle)
    def color(self, value): color(value)
    def pensize(self, value): pensize(value)
    def circle(self, radius, steps=36): circle(radius, steps)


class _Screen:
    def bye(self):
        pass


def Screen():
    return _Screen()


atexit.register(done)
"""


class RunnerUnavailable(Exception):
    pass


class RunnerError(Exception):
    pass


class UnixHTTPAdapterCompat(docker.transport.unixconn.UnixHTTPAdapter):
    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        return self.get_connection(request.url, proxies)


def runner_diagnostics() -> dict:
    host = _normalize_host()
    socket_path = None
    socket_exists = None
    socket_is_socket = None
    socket_mode = None
    socket_uid = None
    socket_gid = None
    if host.startswith(("unix://", "http+unix://")):
        socket_path = host.replace("http+unix://", "", 1).replace("unix://", "", 1)
        try:
            stat_result = os.stat(socket_path)
            socket_exists = True
            socket_is_socket = stat.S_ISSOCK(stat_result.st_mode)
            socket_mode = oct(stat_result.st_mode & 0o777)
            socket_uid = stat_result.st_uid
            socket_gid = stat_result.st_gid
        except OSError:
            socket_exists = os.path.exists(socket_path)

    diagnostics = {
        "runner_enabled": config.RUNNER_ENABLED,
        "docker_py_version": getattr(docker, "__version__", "unknown"),
        "requests_version": getattr(requests, "__version__", "unknown"),
        "runner_docker_host": config.RUNNER_DOCKER_HOST,
        "runner_docker_api_version": config.RUNNER_DOCKER_API_VERSION,
        "normalized_host": host,
        "socket_path": socket_path,
        "socket_exists": socket_exists,
        "socket_is_socket": socket_is_socket,
        "socket_mode": socket_mode,
        "socket_uid": socket_uid,
        "socket_gid": socket_gid,
        "proxy_env": {
            "HTTP_PROXY": os.getenv("HTTP_PROXY"),
            "HTTPS_PROXY": os.getenv("HTTPS_PROXY"),
            "NO_PROXY": os.getenv("NO_PROXY"),
            "http_proxy": os.getenv("http_proxy"),
            "https_proxy": os.getenv("https_proxy"),
            "no_proxy": os.getenv("no_proxy"),
        },
    }

    try:
        client = _client()
        diagnostics["client_base_url"] = client.base_url
        diagnostics["client_adapters"] = sorted(client.adapters.keys())
        try:
            adapter = client.get_adapter(client.base_url)
            diagnostics["adapter_for_base_url"] = adapter.__class__.__name__
        except Exception as exc:
            diagnostics["adapter_error"] = str(exc)
        try:
            diagnostics["server_version"] = client.version()
        except Exception as exc:
            diagnostics["server_version_error"] = str(exc)
    except Exception as exc:
        diagnostics["client_error"] = str(exc)

    return diagnostics


def _normalize_host() -> str:
    host = (config.RUNNER_DOCKER_HOST or "").strip()
    if not host:
        host = "unix:///var/run/docker.sock"
    if host.startswith("/"):
        host = f"unix://{host}"
    if host.startswith("unix://") and not host.startswith("unix:///"):
        host = "unix:///" + host[len("unix://") :].lstrip("/")
    return host


def _ensure_socket():
    host = _normalize_host()
    if host.startswith(("unix://", "http+unix://")):
        socket_path = host.replace("http+unix://", "", 1).replace("unix://", "", 1)
        if not os.path.exists(socket_path):
            raise RunnerUnavailable(f"Docker socket not available at {socket_path}.")
        try:
            mode = os.stat(socket_path).st_mode
            if not stat.S_ISSOCK(mode):
                raise RunnerUnavailable(f"Docker socket path is not a socket: {socket_path}.")
        except OSError as exc:
            raise RunnerUnavailable(f"Unable to access Docker socket: {socket_path}.") from exc


def _force_docker_base_url(client, host: str) -> None:
    socket_url = host
    if socket_url.startswith("unix://"):
        socket_url = "http+unix://" + socket_url[len("unix://") :]
    if not socket_url.startswith("http+unix://"):
        return
    adapter = UnixHTTPAdapterCompat(socket_url)
    client.mount("http+docker://", adapter)
    for proto in ("http://", "https://"):
        if proto in client.adapters:
            client.adapters.pop(proto)
    client.base_url = "http+docker://localhost"
    client._custom_adapter = adapter


def _client():
    _ensure_socket()
    try:
        host = _normalize_host()
        client = docker.APIClient(
            base_url=host,
            version=config.RUNNER_DOCKER_API_VERSION or "auto",
        )
        if host.startswith(("unix://", "http+unix://")):
            # Avoid proxy injection breaking http+docker schemes for local sockets.
            client.trust_env = False
            client.proxies = {}
            _force_docker_base_url(client, host)
        return client
    except (DockerException, ValueError) as exc:
        raise RunnerUnavailable(f"Docker client unavailable: {exc}") from exc


def _safe_path(path: str) -> str:
    cleaned = (path or "").strip().replace("\\", "/")
    if not cleaned or cleaned.startswith("/") or cleaned.startswith("./") or cleaned.startswith("../"):
        raise ValueError("Invalid file path.")
    if "/../" in cleaned or cleaned == "..":
        raise ValueError("Invalid file path.")
    if not SAFE_PATH.match(cleaned):
        raise ValueError("Invalid file path.")
    return cleaned


def _sanitize_files(files: List[dict]) -> List[dict]:
    if not files:
        return []
    if not isinstance(files, list):
        raise ValueError("Files must be a list.")
    if len(files) > config.RUNNER_MAX_FILES:
        raise ValueError("Too many files.")
    cleaned = []
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Invalid file entry.")
        path = _safe_path(item.get("path", ""))
        content = item.get("content", "")
        if not isinstance(content, str):
            raise ValueError("Invalid file content.")
        payload = content.encode("utf-8")
        if len(payload) > config.RUNNER_MAX_FILE_BYTES:
            raise ValueError("File too large.")
        cleaned.append({"path": path, "content": content})
    return cleaned


def _add_text(tar: tarfile.TarFile, name: str, content: str):
    data = content.encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))


def _build_archive(code: str, files: List[dict]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        _add_text(tar, "main.py", code)
        _add_text(tar, "turtle.py", TURTLE_STUB)
        for entry in files:
            _add_text(tar, entry["path"], entry["content"])
    buf.seek(0)
    return buf.read()


def _build_exec_command(code: str) -> tuple[list[str], dict]:
    runner_bootstrap = (
        "import base64,os,shutil\n"
        "payload=os.environ.get('TLAC_CODE_B64','')\n"
        "text=base64.b64decode(payload.encode('ascii')).decode('utf-8','replace') if payload else ''\n"
        "path='/tmp/main.py'\n"
        "try:\n"
        "    with open(path,'w',encoding='utf-8') as handle:\n"
        "        handle.write(text)\n"
        "except Exception:\n"
        "    pass\n"
        "try:\n"
        "    os.chdir('/tmp')\n"
        "except Exception:\n"
        "    pass\n"
        "cwd=os.getcwd()\n"
        "def _snapshot(root):\n"
        "    files=set()\n"
        "    for base, _, names in os.walk(root):\n"
        "        for name in names:\n"
        "            full=os.path.join(base,name)\n"
        "            try:\n"
        "                rel=os.path.relpath(full, root)\n"
        "            except Exception:\n"
        "                rel=name\n"
        "            files.add(rel)\n"
        "    return files\n"
        "before=_snapshot(cwd)\n"
        "globals_dict={'__name__':'__main__','__file__':path}\n"
        "exec(compile(text, path, 'exec'), globals_dict)\n"
        "after=_snapshot(cwd)\n"
        "if cwd != '/tmp':\n"
        "    for rel in sorted(after - before):\n"
        "        src=os.path.join(cwd, rel)\n"
        "        dst=os.path.join('/tmp', rel)\n"
        "        try:\n"
        "            dirpath=os.path.dirname(dst)\n"
        "            if dirpath:\n"
        "                os.makedirs(dirpath, exist_ok=True)\n"
        "            shutil.copy2(src, dst)\n"
        "        except Exception:\n"
        "            pass\n"
    )
    command = [
        "timeout",
        "-s",
        "SIGKILL",
        f"{config.RUNNER_TIMEOUT_SEC}s",
        "python",
        "-c",
        runner_bootstrap,
    ]
    env = {
        "TLAC_CODE_B64": base64.b64encode(code.encode("utf-8")).decode("ascii"),
    }
    return command, env


def _read_archive(stream, max_bytes: int) -> bytes:
    buf = io.BytesIO()
    size = 0
    for chunk in stream:
        size += len(chunk)
        if size > max_bytes:
            raise RunnerError("Output archive too large.")
        buf.write(chunk)
    buf.seek(0)
    return buf.read()


def _mime_for(path: str) -> str:
    path = path.lower()
    if path.endswith(".svg"):
        return "image/svg+xml"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".jpg") or path.endswith(".jpeg"):
        return "image/jpeg"
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".txt") or path.endswith(".csv") or path.endswith(".md"):
        return "text/plain"
    return "text/plain"


def run_python(code: str, files: List[dict]) -> dict:
    if not config.RUNNER_ENABLED:
        raise RunnerUnavailable("Python runner disabled.")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Code is required.")
    if len(code) > config.RUNNER_MAX_CODE_SIZE:
        raise ValueError("Code too large.")

    cleaned_files = _sanitize_files(files)
    archive = _build_archive(code, cleaned_files)

    client = _client()
    if config.RUNNER_AUTO_PULL:
        try:
            client.pull(config.RUNNER_IMAGE)
        except ImageNotFound:
            raise RunnerUnavailable("Runner image not found.")
        except APIError:
            raise RunnerUnavailable("Unable to pull runner image.")

    tmpfs_opts = {
        "/tmp": f"rw,mode=1777,size={config.RUNNER_TMPFS_MB}m",
    }
    exec_command, exec_env = _build_exec_command(code)
    nano_cpus = max(1, int(config.RUNNER_CPUS * 1_000_000_000))
    host_config = client.create_host_config(
        network_mode="none",
        tmpfs=tmpfs_opts,
        mem_limit=f"{config.RUNNER_MEMORY_MB}m",
        nano_cpus=nano_cpus,
        pids_limit=config.RUNNER_PIDS_LIMIT,
        cap_drop=["ALL"],
        security_opt=["no-new-privileges"],
    )

    container_id = None
    start = time.monotonic()
    timed_out = False
    stdout = ""
    stderr = ""
    exit_code = None
    try:
        container = client.create_container(
            image=config.RUNNER_IMAGE,
            command=["/bin/sh", "-c", "sleep 3600"],
            working_dir="/tmp",
            user="65534:65534",
            environment={
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
            },
            host_config=host_config,
        )
        container_id = container.get("Id")
        client.start(container_id)
        uploaded = client.put_archive(container_id, "/tmp", archive)
        if not uploaded:
            raise RunnerError("Failed to upload code to runner.")
        exec_info = client.exec_create(
            container_id,
            cmd=exec_command,
            workdir="/tmp",
            user="65534:65534",
            environment={
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
                **exec_env,
            },
        )
        exec_id = exec_info.get("Id")
        if not exec_id:
            raise RunnerError("Failed to start runner process.")
        exec_output = client.exec_start(exec_id, demux=True)
        deadline = time.monotonic() + config.RUNNER_TIMEOUT_SEC + 2
        exec_result = client.exec_inspect(exec_id)
        while exec_result.get("Running") and time.monotonic() < deadline:
            time.sleep(0.05)
            exec_result = client.exec_inspect(exec_id)
        exit_code = exec_result.get("ExitCode")
        if exec_result.get("Running"):
            timed_out = True
            try:
                client.kill(container_id)
            except Exception:
                pass
            exit_code = 137

        if isinstance(exec_output, tuple):
            stdout_bytes, stderr_bytes = exec_output
        else:
            stdout_bytes, stderr_bytes = exec_output, b""
        stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
        stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")
        if len(stdout) > config.RUNNER_MAX_OUTPUT:
            stdout = stdout[: config.RUNNER_MAX_OUTPUT] + "\n...[truncated]"
        if len(stderr) > config.RUNNER_MAX_OUTPUT:
            stderr = stderr[: config.RUNNER_MAX_OUTPUT] + "\n...[truncated]"

        stream, _ = client.get_archive(container_id, "/tmp")
        archive_bytes = _read_archive(stream, config.RUNNER_MAX_ARCHIVE_BYTES)
    except DockerException as exc:
        raise RunnerUnavailable(f"Docker execution failed: {exc}") from exc
    finally:
        if container_id:
            try:
                client.remove_container(container_id, force=True)
            except Exception:
                pass

    duration_ms = int((time.monotonic() - start) * 1000)
    files_out = []

    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:*") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = member.name.lstrip("./")
            if name.startswith("tmp/"):
                name = name[len("tmp/") :]
            name = name.lstrip("./")
            if not name:
                continue
            if name in {"main.py", "turtle.py"}:
                continue
            extracted = tar.extractfile(member)
            if not extracted:
                continue
            content = extracted.read()

            if len(files_out) >= config.RUNNER_MAX_FILES:
                continue
            if len(content) > config.RUNNER_MAX_FILE_BYTES:
                content = content[: config.RUNNER_MAX_FILE_BYTES]
            files_out.append(
                {
                    "path": name,
                    "size": len(content),
                    "mime": _mime_for(name),
                    "content_base64": base64.b64encode(content).decode("ascii"),
                }
            )

    if exit_code in {124, 137}:
        timed_out = True

    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "files": files_out,
    }
