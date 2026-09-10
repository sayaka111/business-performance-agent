"""Child-process audit boundary for trusted offline Eval execution, not an OS sandbox."""

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


def install_guard(root, *, allow_network=False):
    root = Path(root).resolve()
    libraries = [Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()]
    stats = {
        "denied_operations": 0,
        "network_allowed": allow_network,
        "read_boundary": "isolated runtime copy and Python installation",
    }

    def inside(path, roots):
        return any(path == r or path.is_relative_to(r) for r in roots)

    def deny():
        stats["denied_operations"] += 1
        raise PermissionError("Offline Eval isolation boundary denied an operation")

    def audit(event, args):
        if event == "open" and not isinstance(args[0], int):
            path = Path(os.fsdecode(args[0])).resolve()
            mode = args[1] or ""
            flags = args[2] if len(args) > 2 else 0
            writing = any(c in str(mode) for c in "wax+") or bool(
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            )
            if not inside(path, [root] if writing else [root, *libraries]):
                deny()
        elif event in ("os.listdir", "os.scandir"):
            value = args[0] if args else root
            if (
                value is not None
                and not isinstance(value, int)
                and not inside(Path(os.fsdecode(value)).resolve(), [root, *libraries])
            ):
                deny()
        elif event == "sqlite3.connect":
            value = os.fsdecode(args[0])
            if value.startswith("file:"):
                value = unquote(urlparse(value).path)
                if (
                    os.name == "nt"
                    and value.startswith("/")
                    and len(value) > 2
                    and value[2] == ":"
                ):
                    value = value[1:]
            if not inside(Path(value).resolve(), [root]):
                deny()
        elif (event.startswith("socket.") and not allow_network) or event in (
            "subprocess.Popen",
            "os.system",
            "os.exec",
            "os.posix_spawn",
        ):
            deny()

    sys.addaudithook(audit)
    return stats
