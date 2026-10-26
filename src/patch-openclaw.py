#!/usr/bin/env python3
"""Exact, reversible OpenClaw 2026.10.7 CONFIG_PID_NS=n compatibility patch.

Run in the Ubuntu rootfs (not Android's Python-less host):
  python3 patch-openclaw.py --check
  python3 patch-openclaw.py --apply
  python3 patch-openclaw.py --restore
Only the pinned distribution modules are changed. No state/config is read.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

FILES = {
    "dist/gateway-state-owner-apzoUqhD.mjs": ("fs", "a8b685ee41d447e48f9a0b1b30e5823e54a73ed9fce96c0645a783010429b600"),
    "dist/native-hook-relay/sqlite-snapshot-staging-owner-BS2I69ac.mjs": ("fsSync", "ebfac5a040bbf3c0c20d7b5c67c8d6ac8e62bd2c2a6f4834164354da3168e50b"),
    "dist/managed-handoff-runtime.mjs": ("fs", "aacd9639ea197202ab598fcdde4077230caf7e21a68754355d5c724abb57fad6"),
    "dist/package-update-activation-recovery.mjs": ("fs", "a69120f7e94879553ad42d0a28d7889c112d1af81e5f577caaac7c5b75b44fcc"),
    "dist/infra/sqlite-readonly-location.worker.js": ("fs", "afe1ab1a0691c31d742d5cc95199ff6cd8fcca23e6a1dd2f818ce6cbb7cc9b9d"),
    "dist/state/openclaw-state-read.worker.js": ("fs", "95b606f91197936cbd97471fe09641b599a11ee37dd6deba4e083395c507f179"),
    "dist/state/openclaw-state-lease-heartbeat.worker.js": ("fs", "53eb005ef09f780af3909fac85f48b825d17a7e9e0e6c5a95201a237bdec81cc"),
    "dist/process/supervisor/service-child-group-anchor.js": ("fs", "05de15937abde911df5011ced3679763cbfa02f38e80f715cd91f88562ca42e5"),
}
MARKER = "ksu-kernel-CONFIG_PID_NS=n-v1"
BACKUP = ".ksu-no-pidns-v1.orig"
IMPORT = 'import { gunzipSync as ksuGatewayGunzipSync } from "node:zlib";\n'
# The token describes a verified kernel capability, not a fabricated proc inode.
# PID and birth ticks remain in upstream payload.pid/startTime/startedAt.
HELPERS = r'''// KSU CONFIG_PID_NS=n compatibility v1; real PID namespaces stay upstream.
function ksuGatewayReadStartTicks(pid, pathname = `/proc/${pid}/stat`) {
	if (!Number.isSafeInteger(pid) || pid <= 0) throw new Error("Invalid Gateway PID");
	const raw = @FS@.readFileSync(pathname, "utf8");
	const end = raw.lastIndexOf(")");
	if (!raw.startsWith(`${pid} (`) || end < 0) throw new Error("Invalid Gateway proc stat");
	const ticks = raw.slice(end + 1).trimStart().split(/\s+/)[19];
	if (!/^[0-9]+$/.test(ticks ?? "") || !Number.isSafeInteger(Number(ticks))) throw new Error("Invalid Gateway birth ticks");
	return Number(ticks);
}
function ksuGatewayPidNamespaceIdentity() {
	try {
		return @FS@.statSync("/proc/self/ns/pid", { bigint: true }).ino.toString();
	} catch (error) {
		if (error?.code !== "ENOENT") throw error;
		const config = ksuGatewayGunzipSync(@FS@.readFileSync("/proc/config.gz"), { maxOutputLength: 8388608 }).toString("utf8");
		if (!/^# CONFIG_PID_NS is not set$/m.test(config) || /^CONFIG_PID_NS=/m.test(config)) throw error;
		const ticks = ksuGatewayReadStartTicks(process.pid, "/proc/self/stat");
		if (ksuGatewayReadStartTicks(process.pid) !== ticks || getFileLockProcessStartTime(process.pid) !== ticks) throw error;
		return "ksu-kernel-CONFIG_PID_NS=n-v1";
	}
}
'''
STRICT = r'''	if (namespace === "same" && payload?.processNamespace?.pidNsInode === "ksu-kernel-CONFIG_PID_NS=n-v1") {
		if (!Number.isSafeInteger(payload.pid) || payload.pid <= 0 || !Number.isSafeInteger(payload.startTime) || payload.startTime < 0) throw new GatewayLockNamespaceError(payload, lockPath);
		try {
			if (ksuGatewayReadStartTicks(payload.pid) !== payload.startTime) return true;
		} catch (error) {
			if (error?.code === "ENOENT" || error?.code === "ESRCH") {
				try { process.kill(payload.pid, 0); } catch (probe) { if (probe?.code === "ESRCH") return true; }
			}
			throw new GatewayLockNamespaceError(payload, lockPath);
		}
	}
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def edits(alias):
    anchor = "function readGatewayLockProcessNamespace() {"
    probe = f'{alias}.statSync("/proc/self/ns/pid", {{ bigint: true }}).ino.toString()'
    stale = '\tif (namespace === "unknown") throw new GatewayLockNamespaceError(payload ?? {}, lockPath);\n'
    return [
        (anchor, HELPERS.replace("@FS@", alias) + anchor),
        # The helpers contain the same original probe; replace only the spread.
        (f'{{ pidNsInode: {probe} }}', '{ pidNsInode: ksuGatewayPidNamespaceIdentity() }'),
        (stale, stale + STRICT),
    ]


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one anchor, got {count}")
    return text.replace(old, new, 1)


def transform(data, alias, reverse=False):
    text = data.decode("utf-8")
    if reverse:
        if not text.startswith(IMPORT):
            raise ValueError("missing exact patch import")
        text = text[len(IMPORT):]
    pairs = list(edits(alias))
    if reverse:
        pairs = [(new, old) for old, new in reversed(pairs)]
    for index, (old, new) in enumerate(pairs):
        text = replace_once(text, old, new, f"edit {index + 1}")
    return (text if reverse else IMPORT + text).encode("utf-8")


def atomic_write(path, data, metadata):
    fd, name = tempfile.mkstemp(prefix=".ksu-pidns-", suffix=".mjs", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            os.fchmod(stream.fileno(), metadata.st_mode & 0o7777)
            os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path, default=Path("/usr/local/lib/node_modules/openclaw"))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--apply", action="store_true")
    action.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    base = args.package_dir.resolve(strict=True)
    if json.loads((base / "package.json").read_text())["version"] != "2026.10.7":
        raise ValueError("unsupported OpenClaw version; refusing to patch")
    plans = []
    # Validate ALL modules and backups before making any changes.
    for rel, (alias, original_hash) in FILES.items():
        path = base / rel
        if path.is_symlink() or path.resolve(strict=True).parent != path.parent.resolve():
            raise ValueError(f"{rel}: unexpected symlink")
        current = path.read_bytes()
        original = current if sha(current) == original_hash else transform(current, alias, reverse=True)
        if sha(original) != original_hash:
            raise ValueError(f"{rel}: original SHA256 mismatch; refusing to patch")
        patched = transform(original, alias)
        if current not in (original, patched):
            raise ValueError(f"{rel}: noncanonical patch; refusing to patch")
        backup = path.with_name(path.name + BACKUP)
        if backup.exists() and (backup.is_symlink() or backup.read_bytes() != original):
            raise ValueError(f"{rel}: backup mismatch; refusing to overwrite")
        target = original if args.restore else patched
        plans.append((path, current, original, target, backup, path.stat()))
        print(f"{'PATCHED' if current == patched else 'ORIGINAL'} {rel} sha256={sha(current)}")
    if args.check:
        print(f"CHECK OK: {len(FILES)} exact pinned modules; no changes")
        return
    # Compile candidates first, without importing/executing any OpenClaw module.
    with tempfile.TemporaryDirectory(prefix="ksu-pidns-check-") as tmp:
        for index, (_, _, _, target, _, _) in enumerate(plans):
            candidate = Path(tmp) / f"{index}.mjs"
            candidate.write_bytes(target)
            subprocess.run(["node", "--check", str(candidate)], check=True)
    for path, current, original, target, backup, metadata in plans:
        if path.read_bytes() != current:
            raise ValueError(f"{path.name}: changed during verification")
        if current == target:
            continue
        if args.apply and not backup.exists():
            with backup.open("xb") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(original)
                stream.flush()
                os.fsync(stream.fileno())
        atomic_write(path, target, metadata)
        print(f"WROTE {path.relative_to(base)} sha256={sha(target)}")
    print("RESTORE OK" if args.restore else "APPLY OK (idempotent)")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"REFUSED: {error}")
