import os
from contextlib import suppress
from pathlib import Path


def file_switch(path: Path) -> None:
    if path.exists():
        path.unlink()
    else:
        path.touch()


def remove_empty_directories(path: Path) -> None:
    exclude = {
        "\\.",
        "\\_",
        "\\__",
    }
    for dir_path, dir_names, file_names in os.walk(
        path,
        topdown=False,
    ):
        dir_path = Path(dir_path)
        if any(i in str(dir_path) for i in exclude):
            continue
        dir_names = [Path(dir_name) for dir_name in dir_names]
        if not dir_names and not file_names:
            with suppress(OSError):
                dir_path.rmdir()
