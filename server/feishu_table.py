from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID", "cli_a5d2851ae93a900c")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "hSROo4WwzjbVCdqg1aZIffLhFAGUbT0O")
APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "Pyw7bsxDiaSkKXsBwUqc9DH4n5c")
TABLE_ID = os.getenv("FEISHU_TABLE_ID", "tblm8VXL99Bt9lcK")
XHS_APP_TOKEN = os.getenv("FEISHU_XHS_APP_TOKEN", "OugZbH7a5aY3Ctsqziucq2WGnGh")
XHS_TABLE_ID = os.getenv("FEISHU_XHS_TABLE_ID", "tblS0MEBItXCaxIN")

FIELD_ATTACHMENT = os.getenv("FEISHU_FIELD_ATTACHMENT", "视频")
FIELD_REMARK = os.getenv("FEISHU_FIELD_REMARK", "备注")
FIELD_VIDEO_ID = os.getenv("FEISHU_FIELD_VIDEO_ID", "video_id")
FIELD_PRODUCT_NAME = os.getenv("FIELD_PRODUCT_NAME", "品")
FIELD_TITLE = os.getenv("FIELD_TITLE", "原爆款标题")

LARGE_FILE_THRESHOLD = 20 * 1024 * 1024


def get_tenant_access_token(app_id: Optional[str] = None, app_secret: Optional[str] = None) -> str:
    """获取 tenant_access_token，用于后续调用所有飞书开放接口。"""
    effective_app_id = app_id or APP_ID
    effective_app_secret = app_secret or APP_SECRET
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    response = requests.post(url, json={"app_id": effective_app_id, "app_secret": effective_app_secret}, timeout=15)
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取tenant_access_token失败: {data.get('code')} {data.get('msg')}")
    return data["tenant_access_token"]


def search_record_by_video_id(
    video_id: str,
    *,
    page_size: int = 1,
    app_token: Optional[str] = None,
    table_id: Optional[str] = None,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """按照 video_id 搜索飞书多维表记录。"""
    effective_app_token = app_token or APP_TOKEN
    effective_table_id = table_id or TABLE_ID
    tenant_token = access_token or get_tenant_access_token()

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{effective_app_token}/tables/{effective_table_id}/records/search"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json",
    }
    body = {
        "filter": {
            "conditions": [
                {"field_name": FIELD_VIDEO_ID, "operator": "is", "value": [video_id]},
            ],
            "conjunction": "and",
        },
        "page_size": page_size,
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=15)
        data = response.json()
        if data.get("code") != 0:
            logging.warning("搜索记录失败 code=%s msg=%s", data.get("code"), data.get("msg"))
            return {"total": 0, "items": [], "error": data.get("msg")}
        payload = data.get("data") or {}
        return {"total": payload.get("total", 0), "items": payload.get("items", [])}
    except Exception as exc:  # pragma: no cover - 网络异常
        logging.error("search_record_by_video_id error: %s", exc)
        return {"total": 0, "items": [], "error": str(exc)}


def upload_file_to_bitable(
    file_path: str,
    file_name: str,
    *,
    parent_node: Optional[str] = None,
    parent_type: str = "bitable_file",
    max_retries: int = 3,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """上传任意文件到多维表素材库（普通上传或分片上传）。"""
    if not file_path or not os.path.isfile(file_path):
        return {"success": False, "file_token": None, "message": "文件不存在或路径非法"}

    file_size = os.path.getsize(file_path)
    tenant_token = access_token or get_tenant_access_token()
    target_parent_node = parent_node or APP_TOKEN

    if file_size > LARGE_FILE_THRESHOLD:
        file_token = _upload_large_file(
            file_path,
            file_name,
            tenant_token,
            parent_node=target_parent_node,
            parent_type=parent_type,
            max_retries=max_retries,
        )
    else:
        file_token = _upload_small_file(
            file_path,
            file_name,
            tenant_token,
            parent_node=target_parent_node,
            parent_type=parent_type,
            max_retries=max_retries,
        )

    upload_success = bool(file_token)
    return {
        "success": upload_success,
        "file_token": file_token if upload_success else None,
        "message": "文件上传成功" if upload_success else "文件上传失败",
        "access_token": tenant_token if upload_success else None,
    }


def create_record(
    fields: Dict[str, Any],
    *,
    access_token: Optional[str] = None,
    app_token: Optional[str] = None,
    table_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """在指定的飞书多维表中创建记录，成功返回 record 数据。"""
    effective_app_token = app_token or APP_TOKEN
    effective_table_id = table_id or TABLE_ID
    tenant_token = access_token or get_tenant_access_token()

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{effective_app_token}/tables/{effective_table_id}/records"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json",
    }
    payload = {"fields": fields}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        if data.get("code") != 0:
            logging.warning("创建飞书记录失败: code=%s msg=%s", data.get("code"), data.get("msg"))
            return None
        return (data.get("data") or {}).get("record")
    except Exception as exc:  # pragma: no cover - 网络异常
        logging.error("create_record error: %s", exc)
        return None


def create_douyin_record(fields: Dict[str, Any], *, access_token: Optional[str] = None) -> bool:
    """创建抖音视频记录，返回操作是否成功。"""
    record = create_record(fields, access_token=access_token, app_token=APP_TOKEN, table_id=TABLE_ID)
    return bool(record)


def create_xhs_record(fields: Dict[str, Any], *, access_token: Optional[str] = None) -> bool:
    """在小红书专用多维表中创建记录。"""
    record = create_record(fields, access_token=access_token, app_token=XHS_APP_TOKEN, table_id=XHS_TABLE_ID)
    return bool(record)


def _upload_large_file(
    file_path: str,
    file_name: str,
    access_token: str,
    *,
    parent_node: str,
    parent_type: str,
    max_retries: int = 3,
) -> Optional[str]:
    file_size = os.path.getsize(file_path)
    if not file_size:
        logging.warning("文件大小为0，跳过分片上传")
        return None

    for attempt in range(max_retries):
        try:
            logging.info("开始飞书分片上传，尝试 %s/%s", attempt + 1, max_retries)
            prepare_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_prepare"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            prepare_data = {
                "file_name": file_name,
                "parent_type": parent_type,
                "parent_node": parent_node,
                "size": file_size,
            }
            prepare_response = requests.post(prepare_url, headers=headers, json=prepare_data, timeout=30)
            prepare_result = prepare_response.json()
            logging.debug("分片预上传响应: %s", prepare_result)

            if prepare_result.get("code") != 0:
                logging.warning("预上传失败: %s", prepare_result.get("msg"))
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                return None

            upload_id = prepare_result["data"]["upload_id"]
            block_size = prepare_result["data"]["block_size"]
            block_num = prepare_result["data"]["block_num"]

            if not _upload_file_parts(file_path, upload_id, block_size, block_num, access_token):
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                return None

            finish_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_finish"
            finish_data = {"upload_id": upload_id, "block_num": block_num}
            finish_response = requests.post(finish_url, headers=headers, json=finish_data, timeout=30)
            finish_result = finish_response.json()
            logging.debug("分片完成响应: %s", finish_result)

            if finish_result.get("code") != 0:
                logging.warning("分片完成失败: %s", finish_result.get("msg"))
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                return None

            logging.info("分片上传完成: %s", finish_result["data"].get("file_token"))
            return finish_result["data"]["file_token"]

        except requests.exceptions.Timeout:
            logging.warning("分片上传超时: 第 %s 次", attempt + 1)
        except requests.exceptions.ConnectionError as error:
            logging.warning("分片上传网络错误: %s", error)
        except Exception as error:  # pragma: no cover
            logging.exception("分片上传异常: %s", error)

        if attempt < max_retries - 1:
            time.sleep((attempt + 1) * 2)

    logging.error("分片上传多次失败，已放弃")
    return None


def _upload_small_file(
    file_path: str,
    file_name: str,
    access_token: str,
    *,
    parent_node: str,
    parent_type: str,
    max_retries: int = 3,
) -> Optional[str]:
    try:
        file_size = os.path.getsize(file_path)
    except Exception:
        file_size = 0

    if not file_size:
        logging.warning("文件大小为0，跳过普通上传")
        return None

    upload_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"

    for attempt in range(max_retries):
        try:
            logging.info("开始飞书素材上传，尝试 %s/%s", attempt + 1, max_retries)
            with open(file_path, "rb") as file_handle:
                files = {"file": (file_name, file_handle, "application/octet-stream")}
                data = {
                    "file_name": file_name,
                    "parent_type": parent_type,
                    "parent_node": parent_node,
                    "size": file_size,
                }
                headers = {"Authorization": f"Bearer {access_token}"}

                response = requests.post(
                    upload_url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=(30, 300),
                )
                result = response.json()
                logging.debug("普通上传响应: %s", result)

                if result.get("code") != 0:
                    logging.warning("普通上传失败: %s", result.get("msg"))
                    if attempt < max_retries - 1:
                        time.sleep((attempt + 1) * 2)
                        continue
                    return None

                return result["data"]["file_token"]

        except requests.exceptions.Timeout:
            logging.warning("普通上传超时: 第 %s 次", attempt + 1)
        except requests.exceptions.ConnectionError as error:
            logging.warning("普通上传网络错误: %s", error)
        except Exception as error:  # pragma: no cover
            logging.exception("普通上传异常: %s", error)

        if attempt < max_retries - 1:
            time.sleep((attempt + 1) * 2)

    logging.error("普通上传多次失败，已放弃")
    return None


def _upload_file_parts(
    file_path: str,
    upload_id: str,
    block_size: int,
    block_num: int,
    access_token: str,
) -> bool:
    upload_part_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_part"

    with open(file_path, "rb") as file_handle:
        for seq in range(block_num):
            chunk_data = file_handle.read(block_size)
            if not chunk_data:
                break

            headers = {"Authorization": f"Bearer {access_token}"}
            files = {"file": (f"part_{seq}", chunk_data, "application/octet-stream")}
            data = {
                "upload_id": upload_id,
                "seq": str(seq),
                "size": str(len(chunk_data)),
            }

            try:
                response = requests.post(
                    upload_part_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=(30, 300),
                )
                result = response.json()
                logging.debug("分片 %s 上传响应: %s", seq + 1, result)

                if result.get("code") != 0:
                    logging.warning("分片 %s 上传失败: %s", seq + 1, result.get("msg"))
                    return False

            except Exception as error:  # pragma: no cover
                logging.exception("分片 %s 上传异常: %s", seq + 1, error)
                return False

    logging.info("所有分片上传完成")
    return True


__all__ = [
    "APP_ID",
    "APP_SECRET",
    "APP_TOKEN",
    "TABLE_ID",
    "XHS_APP_TOKEN",
    "XHS_TABLE_ID",
    "FIELD_ATTACHMENT",
    "FIELD_REMARK",
    "FIELD_VIDEO_ID",
    "get_tenant_access_token",
    "search_record_by_video_id",
    "upload_file_to_bitable",
    "create_record",
    "create_douyin_record",
    "create_xhs_record",
]
