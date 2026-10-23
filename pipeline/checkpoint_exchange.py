"""Offline manual independent custody exchange; no deployment or network I/O."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from pipeline.authority.cli import ROOT, protected_key, trusted_history
from pipeline.authority.ledger import STOP
from pipeline.authority.manual_custodian import (
    CurrentChallenge,
    close,
    consume,
    initialize,
    issue,
    outside,
    prepare_response,
    read_pin,
)
from pipeline.authority.protocol import AuthorityError, canonical, encode64, fingerprint
from pipeline.filesystem import confined_file
from pipeline.generation import bounded_file
from pipeline.operations.custodian import DOMAIN, Receipt, wire


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally embeds arbitrary argument values in diagnostics.
        self.exit(2, "argument_error: Invalid custody arguments; run --help for valid options.\n")


def _write(path, value, root):
    target = outside(path, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Interrupted exports are visibly incomplete; never replace old evidence.
    with target.open("xb") as output:
        output.write(value)
        output.flush()
        os.fsync(output.fileno())


def execute(args, now):
    pin = read_pin(args.pin, args.root)
    path = outside(args.state, args.root)
    if args.action == "initialize":
        # Genesis creation is an explicit ceremony boundary, never recovery.
        if args.confirm_genesis != pin.ledger_id:
            raise AuthorityError("confirmation", "Confirm exact ledger ID after independently verifying empty custody genesis")
        initialize(path, pin, now, root=args.root)
        return {"status": "PASS", "code": "local_genesis_created", "independently_trusted": False,
                "publication_allowed": False}
    _, history = trusted_history(args.root, now)
    stopped = confined_file(args.root, STOP).exists()
    if args.action == "respond":
        checkpoint = bounded_file(outside(args.checkpoint, args.root), 64_000)
        request = bounded_file(outside(args.challenge, args.root), 16_000)
        from pipeline.authority.manual_custodian import sha
        if args.confirm_request != sha(request):
            raise AuthorityError("confirmation", "Inspect the exact request digest before independent custodian signing")
        payload = prepare_response(path, pin, request, checkpoint, history, now, emergency_stopped=stopped)
        private = protected_key(args.key, args.root)
        if fingerprint(private.public_key().public_bytes_raw()) != pin.key.key_id:
            raise AuthorityError("custodian_key", "Signing key differs from the independently authenticated custodian pin")
        receipt = Receipt(algorithm="Ed25519", payload=payload,
                          signature=encode64(private.sign(DOMAIN + canonical(payload.model_dump(mode="json")))))
        raw = wire(receipt)
        # A passphrase prompt does not stop elapsed time or suspend STOP.
        token = consume(path, pin, raw, checkpoint, history, datetime.now(UTC).replace(microsecond=0),
                        expected_nonce=CurrentChallenge.model_validate_json(request).nonce,
                        emergency_stopped=confined_file(args.root, STOP).exists())
        close(path, pin, token)
        _write(args.output, raw, args.root)
        return {"status": "PASS", "code": "independent_receipt_retained_and_exported",
                "publication_allowed": False}
    if not args.command:
        raise AuthorityError("command", "Supply the explicit local operation after --")
    command = args.command[1:] if args.command[0] == "--" else args.command
    if not command:
        raise AuthorityError("command", "Supply an explicit local operation")
    checkpoint_path, receipt_path = outside(args.checkpoint, args.root), outside(args.receipt, args.root)
    challenge_path = outside(args.challenge_output, args.root)
    if any(target.exists() for target in (checkpoint_path, receipt_path, challenge_path)):
        raise AuthorityError("custodian_fresh_paths", "Use fresh absent challenge, checkpoint and receipt paths")
    request = issue(path, pin, history, now, emergency_stopped=stopped)
    # This nonce is created by this run and held in memory until acceptance.
    # A restored pending database cannot choose the expected live challenge.
    expected_nonce = request.nonce
    _write(challenge_path, canonical(request.model_dump(mode="json")), args.root)
    print(json.dumps({"status": "BLOCKED", "code": "awaiting_independent_response",
                      "nonce": request.nonce, "expires_at": request.expires_at,
                      "publication_allowed": False}), flush=True)
    started = time.monotonic()
    from pipeline.authority.protocol import instant
    while True:
        at = datetime.now(UTC).replace(microsecond=0)
        if time.monotonic() - started >= 120 or not instant(request.issued_at) <= at < instant(request.expires_at):
            raise AuthorityError("custodian_response_timeout", "Fresh live exchange expired; never reuse its response")
        if checkpoint_path.is_file() and receipt_path.is_file():
            break
        if confined_file(args.root, STOP).exists():
            raise AuthorityError("emergency_hold", "Emergency STOP interrupted the live exchange")
        time.sleep(0.1)
    _, history = trusted_history(args.root, at)
    checkpoint = bounded_file(checkpoint_path, 64_000)
    receipt = bounded_file(receipt_path, 16_000)
    token = consume(path, pin, receipt, checkpoint, history, at, expected_nonce=expected_nonce,
                    emergency_stopped=confined_file(args.root, STOP).exists())
    environment = dict(os.environ, TECHLINE_CUSTODIAN_PIN_FILE=str(outside(args.pin, args.root)),
                       TECHLINE_CUSTODIAN_STATE_FILE=str(path), TECHLINE_CUSTODIAN_RUN_TOKEN=token)
    try:
        # Explicit argv, no shell. Token is passed privately through the child
        # environment, never command-line arguments, stdout or serialized files.
        result = subprocess.run(command, cwd=args.root, env=environment, check=False)  # noqa: S603
    finally:
        close(path, pin, token)
    return {"status": "PASS" if result.returncode == 0 else "FAIL", "code": "local_operation_completed",
            "operation_exit_code": result.returncode, "publication_allowed": False}


def parser():
    result = _ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=ROOT)
    result.add_argument("--pin", type=Path, required=True)
    result.add_argument("--state", type=Path, required=True)
    sub = result.add_subparsers(dest="action", required=True)
    init = sub.add_parser("initialize")
    init.add_argument("--confirm-genesis", required=True)
    respond = sub.add_parser("respond", help="Independent device only; explicitly sign with an existing encrypted key")
    for name in ("challenge", "checkpoint", "key", "output"):
        respond.add_argument("--" + name, type=Path, required=True)
    respond.add_argument("--confirm-request", required=True)
    run = sub.add_parser("run", help="Hold a fresh challenge live, await its response, then run one local command")
    run.add_argument("--challenge-output", type=Path, required=True)
    run.add_argument("--checkpoint", type=Path, required=True)
    run.add_argument("--receipt", type=Path, required=True)
    run.add_argument("command", nargs=argparse.REMAINDER)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    names = ("TECHLINE_CUSTODIAN_PIN_FILE", "TECHLINE_CUSTODIAN_STATE_FILE")
    previous = {name: os.environ.get(name) for name in names}
    try:
        os.environ[names[0]] = str(outside(args.pin, args.root))
        os.environ[names[1]] = str(outside(args.state, args.root))
        value = execute(args, datetime.now(UTC).replace(microsecond=0))
    except (ValueError, OSError, TypeError, KeyError, EOFError) as error:
        value = {"status": "BLOCKED", "code": getattr(error, "code", "custodian_input_refused"),
                 "detail": "Exchange refused; preserve private evidence and inspect independent custody state",
                 "publication_allowed": False}
    finally:
        for name, saved in previous.items():
            if saved is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = saved
    print(json.dumps(value, ensure_ascii=True, indent=2))
    return 0 if value["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
