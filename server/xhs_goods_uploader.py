"""
小红书商品信息上传到飞书表格
"""
import os
import logging
import requests
from typing import Dict, Any, Optional
import feishu_table as feishu

logger = logging.getLogger(__name__)

# 飞书商品表格配置
FEISHU_GOODS_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "Pyw7bsxDiaSkKXsBwUqc9DH4n5c")
FEISHU_GOODS_TABLE_ID = os.getenv("FEISHU_GOODS_TABLE_ID", "tblbfklJzKavr6dd")


def upload_goods_to_feishu(goods_data: Dict[str, Any], access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    上传商品信息到飞书表格

    Args:
        goods_data: 商品数据
            {
                "goods_id": "商品ID",
                "title": "商品标题",
                "shop_name": "店铺名称",
                "price": "商品价格",
                "sales_volume": "已售数量",
                "goods_url": "商品链接",
                "seller_profile_url": "卖家主页链接"
            }
        access_token: 飞书访问令牌（可选）

    Returns:
        {
            "ok": True/False,
            "record_id": "记录ID",
            "error": "错误信息（如果有）",
            "action": "created" | "skipped"
        }
    """
    try:
        # 获取访问令牌
        if not access_token:
            access_token = feishu.get_tenant_access_token()
            if not access_token:
                return {"ok": False, "error": "无法获取飞书访问令牌"}

        # 检查商品是否已存在（通过商品链接）
        goods_url = goods_data.get("goods_url")
        if goods_url:
            # 使用飞书搜索 API 查询
            search_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_GOODS_APP_TOKEN}/tables/{FEISHU_GOODS_TABLE_ID}/records/search"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            search_body = {
                "filter": {
                    "conditions": [
                        {"field_name": "商品链接", "operator": "is", "value": [goods_url]},
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
                        logger.info(f"商品已存在，跳过上传: {goods_url}")
                        return {
                            "ok": True,
                            "record_id": existing_record_id,
                            "message": "商品已存在",
                            "action": "skipped"
                        }
            except Exception as search_err:
                logger.warning(f"搜索商品失败，继续上传: {search_err}")

        # 准备字段数据
        fields = {}

        # 商品标题
        if goods_data.get("title"):
            fields["商品标题"] = goods_data["title"]

        # 店铺名称
        if goods_data.get("shop_name"):
            fields["店铺名称"] = goods_data["shop_name"]

        # 商品链接
        if goods_data.get("goods_url"):
            fields["商品链接"] = goods_data["goods_url"]

        # 商品价格
        if goods_data.get("price") is not None:
            fields["商品价格"] = str(goods_data["price"])

        # 已售数量
        if goods_data.get("sales_volume") is not None:
            fields["sales_volume"] = str(goods_data["sales_volume"])

        # 对标账号主页链接
        if goods_data.get("seller_profile_url"):
            fields["对标账号主页链接"] = goods_data["seller_profile_url"]

        # 商品图片 - 上传到飞书
        if goods_data.get("image_path"):
            import os
            image_path = goods_data["image_path"]
            if os.path.exists(image_path):
                try:
                    logger.info(f"开始上传商品图片: {image_path}")
                    # 上传图片到飞书
                    upload_result = feishu.upload_file_to_bitable(
                        file_path=image_path,
                        file_name=os.path.basename(image_path),
                        access_token=access_token
                    )

                    if upload_result and upload_result.get("file_token"):
                        file_token = upload_result["file_token"]
                        # 飞书附件字段格式
                        fields["商品图片"] = [{"file_token": file_token}]
                        logger.info(f"商品图片上传成功: {file_token}")
                    else:
                        logger.warning(f"商品图片上传失败: {upload_result}")
                except Exception as img_err:
                    logger.error(f"上传商品图片时出错: {img_err}")
            else:
                logger.warning(f"商品图片文件不存在: {image_path}")

        # 打印准备上传的字段
        logger.info(f"准备创建飞书商品记录，字段: {fields}")

        # 创建记录
        record = feishu.create_record(
            fields,
            access_token=access_token,
            app_token=FEISHU_GOODS_APP_TOKEN,
            table_id=FEISHU_GOODS_TABLE_ID
        )

        if record:
            record_id = record.get("record_id")
            logger.info(f"成功上传商品信息到飞书: {goods_data.get('title')}")
            return {
                "ok": True,
                "record_id": record_id,
                "action": "created"
            }
        else:
            return {"ok": False, "error": "创建飞书记录失败"}

    except Exception as e:
        logger.error(f"上传商品信息到飞书失败: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
