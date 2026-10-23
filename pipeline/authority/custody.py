"""Read-only signing-file protection checks; no key creation or ACL mutation."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

from pipeline.authority.protocol import AuthorityError
from pipeline.filesystem import regular_path
from pipeline.strict_json import strict_json

# Paths travel through the child environment, never through PowerShell source.
# SID comparison avoids translated/localized account names. A broad Allow ACE
# is refused even when a Deny ACE might currently mask it.
_ACL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$current = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$paths = @($env:TECHLINE_CUSTODY_INSPECT_PATH,
    [System.IO.Path]::GetDirectoryName($env:TECHLINE_CUSTODY_INSPECT_PATH))
$checks = @($paths | ForEach-Object {
    $acl = Get-Acl -LiteralPath $_
    $owner = $acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
    $rules = @($acl.GetAccessRules($true, $true,
        [System.Security.Principal.SecurityIdentifier]) | ForEach-Object {
        @{sid=$_.IdentityReference.Value; allow=($_.AccessControlType -eq 'Allow')}
    })
    @{owner=$owner; rules=$rules}
})
@{current=$current; checks=$checks} | ConvertTo-Json -Depth 5 -Compress
"""


def _windows_acl(path):
    shell = shutil.which("powershell.exe")
    if not shell:
        raise AuthorityError("key_permissions", "Windows ACL inspection is unavailable; signing is refused")
    environment = os.environ.copy()
    environment["TECHLINE_CUSTODY_INSPECT_PATH"] = str(path)
    try:
        completed = subprocess.run(  # noqa: S603 - fixed script; no input is executable source
            [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", _ACL_SCRIPT],
            env=environment, capture_output=True, timeout=15, check=True)
        value = strict_json(completed.stdout, max_bytes=64_000)
        if (type(value) is not dict or type(value.get("current")) is not str
                or not value["current"].startswith("S-1-") or len(value.get("checks", [])) != 2):
            raise ValueError("Invalid ACL result")
        allowed = {value["current"], "S-1-5-18", "S-1-5-32-544"}  # current user, SYSTEM, administrators
        for checked in value["checks"]:
            if checked["owner"] not in allowed or not checked["rules"]:
                raise ValueError("Untrusted owner or empty/null DACL")
            if not any(rule["allow"] and rule["sid"] == value["current"] for rule in checked["rules"]):
                raise ValueError("No explicit current-user access")
            if any(rule["allow"] and rule["sid"] not in allowed for rule in checked["rules"]):
                raise ValueError("Other identities have access")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        raise AuthorityError("key_permissions", "Signing file or parent ACL is unsafe or unverifiable") from None


def protected_file(path, root):
    """Return an existing regular file after checking its location and access.

    This does not protect against current-user malware, administrators, storage
    snapshots, network administrators or a race by another privileged process.
    """
    path = regular_path(path)
    root = Path(root).absolute()
    if path.is_relative_to(root) or any((parent / ".git").exists() for parent in path.parents):
        raise AuthorityError("key_location", "Signing files must be outside every Git checkout")
    if str(path).startswith(("\\\\", "//")):
        raise AuthorityError("key_location", "Use locally controlled signing storage, not a network share")
    synchronized = [os.environ.get(name) for name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")]
    if (any(location and path.is_relative_to(Path(location).absolute()) for location in synchronized)
            or any(part.casefold() in {"onedrive", "dropbox", "google drive"} for part in path.parts)):
        raise AuthorityError("key_location", "Signing storage must not use a known synchronized directory")
    if not path.is_file():
        raise AuthorityError("key_location", "Signing file does not exist")
    if os.name == "nt":
        _windows_acl(path)
    else:
        for entry in (path, path.parent):
            details = entry.stat()
            if details.st_uid != os.getuid() or details.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise AuthorityError("key_permissions", "Signing file and parent must be owner-only")
    return path
