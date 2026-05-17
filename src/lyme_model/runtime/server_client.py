"""Client for connecting to the persistent model server."""

import json
import os
import socket
import time
from pathlib import Path


def _get_socket_dir():
    return Path.cwd() / ".lyme" / "model"


def get_socket_path():
    return _get_socket_dir() / "server.sock"


def get_pid_path():
    return _get_socket_dir() / "server.pid"


def is_server_running() -> bool:
    sock_path = get_socket_path()
    if not sock_path.exists():
        return False
    try:
        result = send_request({"command": "ping"}, timeout=3)
        return result.get("status") == "ok"
    except (ConnectionRefusedError, FileNotFoundError, TimeoutError, OSError):
        _cleanup_stale_socket()
        return False


def _cleanup_stale_socket():
    sock_path = get_socket_path()
    pid_path = get_pid_path()
    for p in [sock_path, pid_path]:
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass


def send_request(data: dict, timeout: float = 30) -> dict:
    sock_path = get_socket_path()
    if not sock_path.exists():
        raise FileNotFoundError(f"Server socket not found at {sock_path}")

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(sock_path))
        payload = json.dumps(data) + "\n"
        sock.sendall(payload.encode())

        response_data = b""
        while True:
            try:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                response_data += chunk
                if b"\n" in chunk:
                    break
            except socket.timeout:
                raise TimeoutError(f"Server did not respond within {timeout}s")

        if not response_data:
            raise RuntimeError("Empty response from server")

        return json.loads(response_data.decode().strip())
    except socket.timeout:
        raise TimeoutError(f"Server did not respond within {timeout}s")
    finally:
        try:
            sock.close()
        except OSError:
            pass


def send_generate(prompt: str, gen_kwargs: dict, timeout: float = 180) -> dict:
    response = send_request({
        "command": "generate",
        "prompt": prompt,
        "gen_kwargs": gen_kwargs,
    }, timeout=timeout)

    if response.get("status") == "error":
        raise RuntimeError(response.get("error", "Unknown server error"))
    if response.get("status") != "ok":
        raise RuntimeError(f"Unexpected server response: {response}")

    return {
        "output": response["output"],
        "prompt_tokens": response["prompt_tokens"],
        "generated_tokens": response["generated_tokens"],
    }


def get_server_status(timeout: float = 5) -> dict:
    """Get detailed server status including socket path, pid, model, quant mode, uptime, VRAM/RAM."""
    stats = get_server_stats(timeout=timeout)
    if stats.get("status") == "ok":
        stats["socket_path"] = str(get_socket_path())
    return stats


def send_shutdown(timeout: float = 5):
    try:
        send_request({"command": "shutdown"}, timeout=timeout)
    except (ConnectionRefusedError, FileNotFoundError, TimeoutError, OSError):
        pass
    _cleanup_stale_socket()


def get_server_stats(timeout: float = 5) -> dict:
    try:
        return send_request({"command": "stats"}, timeout=timeout)
    except (ConnectionRefusedError, FileNotFoundError, TimeoutError, OSError):
        return {"status": "error", "error": "Server not running"}
