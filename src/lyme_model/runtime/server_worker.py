#!/usr/bin/env python3
"""Persistent model server — loads model once, handles requests via Unix socket.

Usage:
  python -m lyme_model.runtime.server_worker \\
      --model Qwen/Qwen2.5-Coder-1.5B \\
      --socket-path /path/to/.lyme/model/server.sock
"""

import json
import os
import sys
import socket
import time
import traceback
import gc
import argparse
from pathlib import Path

import torch

try:
    from model_worker import load_model, generate_text, cleanup
    from text_cleanup import clean_generated_output
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from model_worker import load_model, generate_text, cleanup
    from text_cleanup import clean_generated_output


def _recv_request(conn):
    data = b""
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            break
        data += chunk
        if b"\n" in data:
            idx = data.find(b"\n")
            return data[:idx]
    return data


def main():
    parser = argparse.ArgumentParser(description="Lyme persistent model server")
    parser.add_argument("--model", required=True, help="Base model name")
    parser.add_argument("--adapter-path", default=None, help="PEFT adapter path")
    parser.add_argument("--socket-path", required=True, help="Unix socket path")
    parser.add_argument("--load-in-4bit", action="store_true", help="4-bit quantization")
    parser.add_argument("--load-in-8bit", action="store_true", help="8-bit quantization")
    parser.add_argument("--dtype", default=None, choices=["float16", "bfloat16", "float32"], help="Torch dtype")
    parser.add_argument("--device", default="auto", help="Device for model")
    parser.add_argument("--debug", action="store_true", help="Verbose errors with traceback")
    args = parser.parse_args()

    offload_dir = str(Path(args.socket_path).parent / "offload")
    init_data = {
        "model_name": args.model,
        "adapter_path": args.adapter_path,
        "device": args.device,
        "offload_dir": offload_dir,
        "debug": args.debug,
        "safe_mode": False,
        "load_in_4bit": args.load_in_4bit,
        "load_in_8bit": args.load_in_8bit,
        "dtype": args.dtype,
    }

    load_start = time.time()
    try:
        model, tokenizer = load_model(init_data)
        load_time = round(time.time() - load_start, 1)
        print(f"Model loaded in {load_time}s: {args.model}", file=sys.stderr, flush=True)
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    start_time = time.time()
    server_socket = None

    try:
        sock_path = Path(args.socket_path)
        sock_path.parent.mkdir(parents=True, exist_ok=True)
        if sock_path.exists():
            sock_path.unlink()

        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_socket.bind(str(sock_path))
        server_socket.listen(5)
        os.chmod(str(sock_path), 0o600)
        print(f"Server listening on {sock_path}", file=sys.stderr, flush=True)

        while True:
            try:
                conn, _ = server_socket.accept()
            except (KeyboardInterrupt, SystemExit):
                break
            except OSError:
                break

            with conn:
                try:
                    raw = _recv_request(conn)
                except OSError:
                    continue

                if not raw:
                    continue

                try:
                    req = json.loads(raw.decode().strip())
                except json.JSONDecodeError:
                    continue

                cmd = req.get("command")

                try:
                    if cmd == "generate":
                        prompt = req["prompt"]
                        gen_kwargs = req.get("gen_kwargs", {})
                        result = generate_text(model, tokenizer, prompt, gen_kwargs)
                        result["output"] = clean_generated_output(result["output"])
                        response = {"status": "ok", **result}

                    elif cmd == "ping":
                        response = {
                            "status": "ok",
                            "pid": os.getpid(),
                            "uptime_s": round(time.time() - start_time, 1),
                        }

                    elif cmd == "stats":
                        vram_allocated_mb = 0
                        vram_reserved_mb = 0
                        if torch.cuda.is_available():
                            vram_allocated_mb = torch.cuda.memory_allocated() // (1024 * 1024)
                            vram_reserved_mb = torch.cuda.memory_reserved() // (1024 * 1024)
                        try:
                            import psutil
                            process = psutil.Process(os.getpid())
                            ram_mb = process.memory_info().rss // (1024 * 1024)
                        except ImportError:
                            ram_mb = 0
                        response = {
                            "status": "ok",
                            "pid": os.getpid(),
                            "model": args.model,
                            "adapter_path": args.adapter_path,
                            "load_time_s": load_time,
                            "vram_allocated_mb": vram_allocated_mb,
                            "vram_reserved_mb": vram_reserved_mb,
                            "ram_mb": ram_mb,
                            "load_in_4bit": args.load_in_4bit,
                            "load_in_8bit": args.load_in_8bit,
                            "dtype": args.dtype or ("float16" if torch.cuda.is_available() else "float32"),
                            "cuda_available": torch.cuda.is_available(),
                            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
                            "uptime_s": round(time.time() - start_time, 1),
                        }

                    elif cmd == "shutdown":
                        response = {"status": "ok", "message": "shutting down"}
                        conn.sendall((json.dumps(response) + "\n").encode())
                        break

                    else:
                        response = {"status": "error", "error": f"Unknown command: {cmd}"}

                except Exception as exc:
                    response = {
                        "status": "error",
                        "error": str(exc),
                        "traceback": traceback.format_exc() if args.debug else None,
                    }

                try:
                    conn.sendall((json.dumps(response) + "\n").encode())
                except OSError:
                    pass

    except KeyboardInterrupt:
        pass
    finally:
        if server_socket is not None:
            try:
                server_socket.close()
            except OSError:
                pass
        try:
            Path(args.socket_path).unlink(missing_ok=True)
        except OSError:
            pass
        cleanup(model, tokenizer)
        print("Server stopped.", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
