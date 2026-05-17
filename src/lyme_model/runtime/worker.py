"""Subprocess worker for Lyme Model — loads model via model_worker, handles stdin/stdout.

This module re-exports shared functions from model_worker for convenience.
Both stdin-based (subprocess) and socket-based (server) workers use the
same model loading and generation code paths.
"""

import json
import sys
import traceback
from pathlib import Path

_runtime_dir = str(Path(__file__).resolve().parent)
if _runtime_dir not in sys.path:
    sys.path.insert(0, _runtime_dir)

from model_worker import load_model, generate_text, cleanup, check_bitsandbytes, resolve_dtype  # noqa: E402


def _respond(data):
    sys.stdout.write(json.dumps(data) + "\n")
    sys.stdout.flush()


def main():
    init = json.loads(sys.stdin.readline())
    assert init.get("command") == "init", f"Expected init command, got: {init}"

    debug = init.get("debug", False)

    try:
        model, tokenizer = load_model(init)
    except RuntimeError as exc:
        response = {"error": str(exc)}
        if debug:
            response["traceback"] = traceback.format_exc()
        _respond(response)
        return

    _respond({"status": "ready"})

    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        cmd = req.get("command")

        if cmd == "generate":
            prompt = req["prompt"]
            gen_kwargs = req.get("gen_kwargs", {})
            try:
                result = generate_text(model, tokenizer, prompt, gen_kwargs)
                _respond({"status": "ok", **result})
            except Exception as exc:
                _respond({
                    "status": "error",
                    "error": str(exc),
                    "traceback": traceback.format_exc() if debug else None,
                })

        elif cmd == "shutdown":
            break

    cleanup(model, tokenizer)


if __name__ == "__main__":
    main()
