#!/usr/bin/env python3
"""Level-triggered review-loop listener with heartbeat-based verification."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any


SCHEMA_VERSION = 1
DEDUPE_KEY_SPEC = "(SESSION_ID, STATUS, ROUND, content hash)"
PROTOCOL_FIELDS = ("SESSION_ID", "STATUS", "ROUND")


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_snapshot(path: Path) -> tuple[str, str, dict[str, str]]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        content = ""

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    fields: dict[str, str] = {}
    for line in content.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in PROTOCOL_FIELDS and key not in fields:
            fields[key] = value.strip()
    return content, digest, fields


def dedupe_key(
    fields: dict[str, str], digest: str
) -> tuple[str, str, str, str]:
    return (
        fields.get("SESSION_ID", ""),
        fields.get("STATUS", ""),
        fields.get("ROUND", ""),
        digest,
    )


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def listen(args: argparse.Namespace) -> int:
    watched = Path(args.watch).resolve()
    state_path = Path(args.state).resolve()
    activation_time = utc_now()
    initial_content, initial_hash, _, = read_snapshot(watched)
    running = True
    seen: set[tuple[str, str, str, str]] = set()

    state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "listener_id": args.listener_id,
        "role": args.role,
        "watched_path": str(watched),
        "status": "RUNNING",
        "activated_at": activation_time,
        "heartbeat_at": activation_time,
        "initial_hash": initial_hash,
        "initial_snapshot": initial_content,
        "dedupe_key": DEDUPE_KEY_SPEC,
        "pid": os.getpid(),
    }

    def request_stop(_signum: int, _frame: Any) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    atomic_write_json(state_path, state)
    emit({"event": "ACTIVATED", **state, "state_path": str(state_path)})

    initial_scan_pending = True
    while running:
        state["heartbeat_at"] = utc_now()
        atomic_write_json(state_path, state)

        content, digest, fields = read_snapshot(watched)
        key = dedupe_key(fields, digest)
        if key not in seen:
            seen.add(key)
            emit(
                {
                    "event": "SCAN",
                    "scan_kind": "INITIAL" if initial_scan_pending else "LEVEL",
                    "listener_id": args.listener_id,
                    "watched_path": str(watched),
                    "content_hash": digest,
                    "content_snapshot": content,
                    "fields": fields,
                    "dedupe_key_value": list(key),
                    "scanned_at": utc_now(),
                }
            )
        initial_scan_pending = False
        time.sleep(args.interval)

    stopped_at = utc_now()
    state["status"] = "STOPPED"
    state["heartbeat_at"] = stopped_at
    state["stopped_at"] = stopped_at
    atomic_write_json(state_path, state)
    emit(
        {
            "event": "STOPPED",
            "listener_id": args.listener_id,
            "watched_path": str(watched),
            "status": "STOPPED",
            "stopped_at": stopped_at,
        }
    )
    return 0


def verification_error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def verify(args: argparse.Namespace) -> int:
    state_path = Path(args.state).resolve()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return verification_error(f"listener state not found: {state_path}")
    except (json.JSONDecodeError, OSError) as exc:
        return verification_error(f"invalid listener state: {exc}")

    required = {
        "schema_version",
        "listener_id",
        "role",
        "watched_path",
        "status",
        "activated_at",
        "heartbeat_at",
        "initial_hash",
        "initial_snapshot",
        "dedupe_key",
        "pid",
    }
    missing = sorted(required.difference(state))
    if missing:
        return verification_error(
            f"listener state missing fields: {', '.join(missing)}"
        )
    if state["schema_version"] != SCHEMA_VERSION:
        return verification_error("schema version mismatch")
    if state["role"] != args.role:
        return verification_error(
            f"role mismatch: expected {args.role}, got {state['role']}"
        )

    expected_watch = str(Path(args.watch).resolve())
    if state["watched_path"] != expected_watch:
        return verification_error(
            "watched path mismatch: "
            f"expected {expected_watch}, got {state['watched_path']}"
        )
    if state["status"] != "RUNNING":
        return verification_error(
            f"listener is not running: status={state['status']}"
        )
    if state["dedupe_key"] != DEDUPE_KEY_SPEC:
        return verification_error("dedupe key specification mismatch")

    try:
        heartbeat = datetime.datetime.fromisoformat(state["heartbeat_at"])
    except (TypeError, ValueError):
        return verification_error("invalid heartbeat timestamp")
    if heartbeat.tzinfo is None:
        return verification_error("heartbeat timestamp is not timezone-aware")

    age = (
        datetime.datetime.now(datetime.timezone.utc)
        - heartbeat.astimezone(datetime.timezone.utc)
    ).total_seconds()
    if age > args.max_age:
        return verification_error(
            f"stale heartbeat: age={age:.3f}s max_age={args.max_age:.3f}s"
        )
    if age < -args.max_age:
        return verification_error(
            f"heartbeat timestamp is in the future: age={age:.3f}s"
        )

    emit(
        {
            "verified": True,
            "listener_id": state["listener_id"],
            "role": state["role"],
            "watched_path": state["watched_path"],
            "heartbeat_age_seconds": age,
        }
    )
    return 0


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    listen_parser = subparsers.add_parser("listen")
    listen_parser.add_argument("--role", choices=("reviewer", "fixer"), required=True)
    listen_parser.add_argument("--watch", required=True)
    listen_parser.add_argument("--state", required=True)
    listen_parser.add_argument("--listener-id", required=True)
    listen_parser.add_argument("--interval", type=positive_float, default=1.0)
    listen_parser.set_defaults(handler=listen)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--state", required=True)
    verify_parser.add_argument(
        "--role", choices=("reviewer", "fixer"), required=True
    )
    verify_parser.add_argument("--watch", required=True)
    verify_parser.add_argument("--max-age", type=positive_float, default=5.0)
    verify_parser.set_defaults(handler=verify)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
