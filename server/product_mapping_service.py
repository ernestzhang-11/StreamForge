import json
import os
import time
from typing import Any, Dict, Optional

CONFIG_FILENAME = "product_mapping.json"
DEFAULT_CHECK_INTERVAL_SECONDS = 30

_product_mapping_cache: Optional[Dict[str, str]] = None
_last_config_mtime: Optional[float] = None
_last_load_timestamp: float = 0.0


def _get_config_path() -> str:
    current_dir = os.path.dirname(__file__)
    return os.path.join(current_dir, CONFIG_FILENAME)


def _should_reload_config(check_interval_seconds: int) -> bool:
    global _last_load_timestamp
    current_timestamp = time.time()
    if current_timestamp - _last_load_timestamp >= check_interval_seconds:
        _last_load_timestamp = current_timestamp
        return True
    return False


def _load_config_from_file(config_path: str) -> Dict[str, str]:
    with open(config_path, "r", encoding="utf-8") as file_handle:
        config_data = json.load(file_handle)
    mapping = config_data.get("product_name_mapping", {})
    if not isinstance(mapping, dict):
        return {}
    normalized_mapping: Dict[str, str] = {}
    for keyword, mapped_value in mapping.items():
        if not isinstance(keyword, str) or not keyword.strip():
            continue
        if not isinstance(mapped_value, str) or not mapped_value.strip():
            continue
        normalized_mapping[keyword.strip()] = mapped_value.strip()
    return normalized_mapping


def load_product_mapping(check_interval_seconds: int = DEFAULT_CHECK_INTERVAL_SECONDS) -> Dict[str, str]:
    global _product_mapping_cache
    global _last_config_mtime

    config_path = _get_config_path()
    if not os.path.exists(config_path):
        _product_mapping_cache = {}
        _last_config_mtime = None
        return {}

    try:
        if _product_mapping_cache is None or _should_reload_config(check_interval_seconds):
            current_mtime = os.path.getmtime(config_path)
            if _last_config_mtime is None or current_mtime != _last_config_mtime:
                _product_mapping_cache = _load_config_from_file(config_path)
                _last_config_mtime = current_mtime
        return _product_mapping_cache or {}
    except Exception:
        _product_mapping_cache = _product_mapping_cache or {}
        return _product_mapping_cache

def extract_product_info(aweme: Dict[str, Any])     :
    """从 aweme 字典中提取首个商品标题，如果不存在则返回 None。"""
    try:
        if not isinstance(aweme, dict):
            return None

        anchor_info = aweme.get("anchor_info")
        if not isinstance(anchor_info, dict):
            return None

        anchor_type = anchor_info.get("type")
        anchor_title_tag = anchor_info.get("title_tag")
        is_product_video = anchor_type == 3 or anchor_title_tag == "购物"
        if not is_product_video:
            return None

        extra_payload = anchor_info.get("extra")
        if not extra_payload:
            return None

        try:
            parsed_extra: Any
            if isinstance(extra_payload, str):
                parsed_extra = json.loads(extra_payload)
            else:
                parsed_extra = extra_payload
        except (json.JSONDecodeError, TypeError):
            return None

        if isinstance(parsed_extra, list):
            for entry in parsed_extra:
                if not isinstance(entry, dict):
                    continue
                title = entry.get("title")
                if isinstance(title, str):
                    normalized_title = title.strip()
                    if normalized_title:
                        return normalized_title
        elif isinstance(parsed_extra, dict):
            title = parsed_extra.get("title")
            if isinstance(title, str):
                normalized_title = title.strip()
                if normalized_title:
                    return normalized_title

        return None
    except Exception:
        return None

def map_product_name(product_name: str, mapping: Dict[str, str]) -> str:
    if not product_name:
        return product_name
    if not mapping:
        return product_name
    for keyword, mapped_value in mapping.items():
        if keyword in product_name:
            return mapped_value
    return product_name


__all__ = [
    "load_product_mapping",
    "map_product_name",
    "extract_product_info"
]
