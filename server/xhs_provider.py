import importlib
import os
import sys
from types import ModuleType


def _try_import(module_name: str) -> ModuleType | None:
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None


def get_xhs_apis_class():
    """
    Resolve XHS_Apis class from preferred sources:
    1) SPIDER_XHS_PATH (local clone/submodule of upstream repo)
    2) Installed module path `apis.xhs_pc_apis` (if available)
    """
    # 1) Env-provided path (e.g., Spider_XHS submodule)
    path = os.getenv("SPIDER_XHS_PATH")
    if not path:
        # Fallback: try project_root/Spider_XHS
        current_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(current_dir, ".."))
        submodule_path = os.path.join(project_root, "Spider_XHS")
        if os.path.isdir(submodule_path):
            path = submodule_path

    if path and os.path.isdir(path):
        # Some upstream modules expect CWD to be repo root to load static JS files.
        # Temporarily chdir into SPIDER_XHS_PATH to import, then restore.
        old_cwd = os.getcwd()
        try:
            if path not in sys.path:
                sys.path.insert(0, path)
            os.chdir(path)
            mod = _try_import("apis.xhs_pc_apis")
            if mod and hasattr(mod, "XHS_Apis"):
                return getattr(mod, "XHS_Apis")
        finally:
            os.chdir(old_cwd)

    # 2) Try import if installed in sys.path
    mod = _try_import("apis.xhs_pc_apis")
    if mod and hasattr(mod, "XHS_Apis"):
        return getattr(mod, "XHS_Apis")

    raise ImportError(
        "Unable to import XHS_Apis. Ensure SPIDER_XHS_PATH is set to the Spider_XHS repo, "
        "or that Spider_XHS submodule exists at project root."
    )

def get_data_spider_class():
    """
    Resolve Data_Spider from Spider_XHS `main.py` for higher-level helpers like `spider_note`.
    Priority is the same as XHS_Apis: SPIDER_XHS_PATH -> installed.
    """
    # 1) Env-provided path (e.g., Spider_XHS submodule)
    path = os.getenv("SPIDER_XHS_PATH")
    if not path:
        # Fallback: try project_root/Spider_XHS
        current_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(current_dir, ".."))
        submodule_path = os.path.join(project_root, "Spider_XHS")
        if os.path.isdir(submodule_path):
            path = submodule_path

    if path and os.path.isdir(path):
        old_cwd = os.getcwd()
        try:
            if path not in sys.path:
                sys.path.insert(0, path)
            os.chdir(path)
            mod = _try_import("main")
            if mod and hasattr(mod, "Data_Spider"):
                return getattr(mod, "Data_Spider")
        finally:
            os.chdir(old_cwd)

    # 2) Try if installed in sys.path
    mod = _try_import("main")
    if mod and hasattr(mod, "Data_Spider"):
        return getattr(mod, "Data_Spider")

    raise ImportError(
        "Unable to import Data_Spider from Spider_XHS. Ensure SPIDER_XHS_PATH is set to the Spider_XHS repo, "
        "or that Spider_XHS submodule exists at project root."
    )
