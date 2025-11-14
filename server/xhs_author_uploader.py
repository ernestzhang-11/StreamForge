"""
小红书作者信息上传到飞书表格
"""
import os
import logging
import requests
from typing import Dict, Any, Optional
import feishu_table as feishu

logger = logging.getLogger(__name__)

# 飞书作者表格配置
FEISHU_AUTHOR_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "Pyw7bsxDiaSkKXsBwUqc9DH4n5c")
FEISHU_AUTHOR_TABLE_ID = os.getenv("FEISHU_AUTHOR_TABLE_ID", "tblgHBLpdBROo42U")


def upload_author_to_feishu(author_data: Dict[str, Any], access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    上传作者信息到飞书表格

    Args:
        author_data: 作者数据
            {
                "user_id": "用户ID",
                "nickname": "昵称",
                "red_id": "小红书号",
                "ip_location": "IP属地",
                "fans_count": 粉丝数
            }
        access_token: 飞书访问令牌（可选）

    Returns:
        {
            "ok": True/False,
            "record_id": "记录ID",
            "error": "错误信息（如果有）"
        }
    """
    try:
        # 获取访问令牌
        if not access_token:
            access_token = feishu.get_tenant_access_token()
            if not access_token:
                return {"ok": False, "error": "无法获取飞书访问令牌"}

        # 检查作者是否已存在（通过小红书号）
        red_id = author_data.get("red_id")

        if red_id:
            # 使用飞书搜索 API 查询
            search_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_AUTHOR_APP_TOKEN}/tables/{FEISHU_AUTHOR_TABLE_ID}/records/search"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            search_body = {
                "filter": {
                    "conditions": [
                        {"field_name": "账号ID", "operator": "is", "value": [red_id]},
                    ],
                    "conjunction": "and",
                },
                "page_size": 1,
            }

            try:
                response = requests.post(search_url, headers=headers, json=search_body, timeout=15)
                data = response.json()
                if data.get("code") == 0:
                    payload = data.get("data", {})
                    total = payload.get("total", 0)
                    if total > 0:
                        items = payload.get("items", [])
                        existing_record_id = items[0].get("record_id") if items else None
                        logger.info(f"作者已存在，跳过上传: {red_id}")
                        return {
                            "ok": True,
                            "record_id": existing_record_id,
                            "message": "作者已存在",
                            "action": "skipped"
                        }
            except Exception as search_err:
                logger.warning(f"搜索作者失败，继续上传: {search_err}")

        # 准备字段数据
        fields = {}

        # 账号名称（昵称）
        if author_data.get("nickname"):
            fields["账号名称"] = author_data["nickname"]

        # 账号ID（小红书号）- 转换为整数
        if author_data.get("red_id"):
            fields["账号ID"] = author_data["red_id"]

        # IP属地
        if author_data.get("ip_location"):
            fields["ip"] = author_data["ip_location"]

        # 粉丝数
        if author_data.get("fans_count") is not None:
            fields["粉丝数"] = str(author_data["fans_count"])

        # 主页链接（从 profile_url 获取，已包含 xsec_token）
        if author_data.get("profile_url"):
            fields["主页链接"] = author_data["profile_url"]
            logger.info(f"准备上传主页链接: {author_data['profile_url']}")

        # 打印准备上传的字段
        logger.info(f"准备创建飞书记录，字段: {fields}")

        # 创建记录
        record = feishu.create_record(
            fields,
            access_token=access_token,
            app_token=FEISHU_AUTHOR_APP_TOKEN,
            table_id=FEISHU_AUTHOR_TABLE_ID
        )

        if record:
            record_id = record.get("record_id")
            logger.info(f"成功上传作者信息到飞书: {author_data.get('nickname')} ({red_id})")
            return {
                "ok": True,
                "record_id": record_id,
                "action": "created"
            }
        else:
            return {"ok": False, "error": "创建飞书记录失败"}

    except Exception as e:
        logger.error(f"上传作者信息到飞书失败: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
