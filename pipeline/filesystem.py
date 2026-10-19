"""Conservative regular-file boundaries, including Windows reparse points.

These checks do not sandbox another process running as the same OS user.
"""

import os
import re
import stat
import tempfile
from pathlib import Path

RESERVED = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.I)


def validate_name_parts(path):
    for part in path.parts:
        if part == path.anchor:
            continue
        if (part.endswith((".", " ")) or RESERVED.match(part)
                or any(ord(char) < 32 or char in '<>:"|?*' for char in part)):
            raise ValueError("Unsafe or reserved filesystem name")


def regular_path(path):
    path = Path(path)
    if ".." in path.parts:
        raise ValueError("Parent traversal is forbidden")
    # Win32 abspath can erase trailing dots/spaces or resolve device aliases.
    # Reject lexical names before applying any OS normalization.
    validate_name_parts(path)
    path = Path(os.path.abspath(path))
    validate_name_parts(path)
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError("Linked filesystem paths are forbidden")
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Reparse filesystem paths are forbidden")
        if candidate == path:
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("File destination collides with a nonregular file")
        elif not stat.S_ISDIR(info.st_mode):
            raise ValueError("Filesystem parent is not a directory")
    return path


def confined_file(root, relative):
    root, relative = Path(root), Path(relative)
    if relative.is_absolute() or relative.drive or ".." in relative.parts:
        raise ValueError("Relative confined path required")
    validate_name_parts(root)
    validate_name_parts(relative)
    root = root.absolute()
    target = regular_path(root / relative)
    if not target.is_relative_to(root):
        raise ValueError("Filesystem path escaped its root")
    return target


def atomic_bytes(path, payload):
    path = regular_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    regular_path(path)
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        regular_path(path)
        Path(temporary).replace(path)
        sync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def sync_directory(directory):
    # Windows does not expose directory fsync through the stdlib. Recovery
    # covers process interruptions; filesystem/power-loss durability is limited
    # by the OS and storage device, and still requires an off-machine backup.
    if os.name != "nt":
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
