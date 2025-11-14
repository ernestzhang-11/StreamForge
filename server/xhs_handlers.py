"""
小红书笔记处理辅助函数
将复杂的处理逻辑拆分为独立的函数
"""
import os
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from xhs_downloader.source import XHS
from xhs_provider import get_xhs_apis_class
from xhs_downloader_util import download_note as download_xhs_note
import feishu_table as feishu

logger = logging.getLogger(__name__)


def parse_note_api_mode(url: str, xhs_cookie: str, download_dir: str) -> Dict[str, Any]:
    """
    API 模式解析小红书笔记

    Args:
        url: 标准化的笔记URL
        xhs_cookie: 小红书Cookie
        download_dir: 下载目录

    Returns:
        解析结果字典
    """
    try:
        if not xhs_cookie:
            return {"ok": False, "error": "缺少 XHS_COOKIE 环境变量（需要包含 a1）"}

        # 获取 API 类
        XHS_Apis = get_xhs_apis_class()
        api = XHS_Apis()

        # 调用 API 获取笔记信息
        success, msg, res_json = api.get_note_info(url, xhs_cookie)

        if not success:
            return {"ok": False, "error": msg or "获取笔记详情失败"}

        # 提取笔记数据
        try:
            note_item = res_json["data"]["items"][0]
        except (KeyError, IndexError, TypeError):
            return {"ok": False, "error": "未获取到笔记数据"}

        # 构建标准化的数据结构
        card = note_item.get("note_card", {})
        user = card.get("user", {})

        item = {
            "作品标题": card.get("title") or "",
            "作品描述": card.get("desc") or "",
            "作品链接": url,
            "作品ID": note_item.get("id") or "",
            "作者昵称": user.get("nickname") or "",
            "点赞数量": (card.get("interact_info") or {}).get("liked_count"),
            "评论数量": (card.get("interact_info") or {}).get("comment_count"),
            "收藏数量": (card.get("interact_info") or {}).get("collected_count"),
            "作品类型": "图文" if card.get("type") == "normal" else "视频",
            "最后更新时间":card.get('last_update_time'),
            "发布时间":card.get('time')
        }

        # 提取媒体URL
        if item["作品类型"] == "视频":
            try:
                origin_key = card["video"]["consumer"]["origin_video_key"]
                item["视频地址url"] = f"https://sns-video-bd.xhscdn.com/{origin_key}"

                image_list = card.get("image_list") or []
                if image_list:
                    item["视频封面url"] = image_list[0]["info_list"][1]["url"]
            except (KeyError, IndexError, TypeError):
                logger.warning("视频URL提取失败")
        else:
            image_list = card.get("image_list") or []
            item["下载地址"] = [
                (img.get("info_list") or [{}])[1].get("url")
                for img in image_list
                if img and img.get("info_list")
            ]

        # 下载媒体文件
        save_path = download_xhs_note(
            note_data=item,
            base_path=os.path.join(download_dir, "xhs"),
            mode="api",
            download_images=True,
            download_videos=True
        )

        if save_path:
            item["文件保存路径"] = save_path
            item["filename"] = os.path.basename(save_path)
            logger.info(f"API模式: 笔记媒体文件已保存到: {save_path}")
        else:
            logger.warning("API模式: 笔记媒体文件下载失败")

        return {"ok": True, "data": [item], "raw": res_json}

    except Exception as e:
        logger.error(f"API模式解析失败: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


def parse_note_web_mode(url: str, xhs_cookie: str, download_dir: str) -> Dict[str, Any]:
    """
    Web 模式解析小红书笔记

    Args:
        url: 标准化的笔记URL
        xhs_cookie: 小红书Cookie
        download_dir: 下载目录

    Returns:
        解析结果字典
    """
    async def _do_parse() -> dict:
        """异步解析函数"""
        async with XHS(
            work_path=download_dir,
            folder_name="xhs",
            name_format="作品标题 发布时间 作品ID",
            user_agent="",
            cookie=xhs_cookie,
            timeout=10,
            chunk=1024 * 1024 * 10,
            max_retry=2,
            image_format="PNG",
            image_download=False,  # 关闭内置下载
            video_download=False,  # 关闭内置下载
            live_download=False,
            download_record=False,
            language="zh_CN",
            read_cookie=None,
        ) as xhs:
            data = await xhs.extract(url, True, cookie=xhs_cookie)
            return {"ok": True, "data": data}

    try:
        # 运行异步解析
        result = asyncio.run(_do_parse())

        # 使用统一的下载方法
        if result.get("ok") and isinstance(result.get("data"), list):
            for item in result["data"]:
                save_path = download_xhs_note(
                    note_data=item,
                    base_path=os.path.join(download_dir, "xhs"),
                    mode="web",
                    download_images=True,
                    download_videos=True
                )

                if save_path:
                    item["文件保存路径"] = save_path
                    item["filename"] = os.path.basename(save_path)
                    logger.info(f"Web模式: 笔记媒体文件已保存到: {save_path}")
                else:
                    logger.warning("Web模式: 笔记媒体文件下载失败")

        return result

    except Exception as e:
        logger.error(f"Web模式解析失败: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


def parse_timestamp(raw) -> Optional[int]:
    """
    解析时间字符串/整数为 Unix 时间戳（毫秒）

    支持格式：
    - "2024-01-01 12:30:45"
    - "2024-01-01_12.30.45"
    - Unix 时间戳字符串
    - Unix 时间戳整数（秒或毫秒）

    Args:
        raw: 原始时间字符串或整数

    Returns:
        Unix 时间戳（毫秒），失败返回 None
    """
    if not raw:
        return None

    # 如果已经是整数，直接返回
    if isinstance(raw, int):
        # 如果是秒级时间戳（10位数），转换为毫秒
        if raw < 10000000000:
            return raw * 1000
        return raw

    # 如果不是字符串，尝试转换
    if not isinstance(raw, str):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    # 标准化时间字符串
    normalized = raw.replace("_", " ")
    parts = normalized.split()
    if len(parts) >= 2:
        parts[1] = parts[1].replace(".", ":")
        normalized = parts[0] + " " + parts[1]
    else:
        normalized = normalized.replace(".", ":")

    # 尝试解析为日期时间
    try:
        dt = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp() * 1000)
    except ValueError:
        pass

    # 尝试解析为数字
    try:
        timestamp = int(float(raw))
        # 如果是秒级时间戳，转换为毫秒
        if timestamp < 10000000000:
            return timestamp * 1000
        return timestamp
    except (TypeError, ValueError):
        return None


def upload_note_to_feishu(note_data: Dict[str, Any], access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    上传笔记到飞书多维表

    Args:
        note_data: 笔记数据
        access_token: 飞书访问令牌（可选）

    Returns:
        上传结果
    """
    try:
        if not access_token:
            access_token = feishu.get_tenant_access_token()

        # 提取基本信息
        title = note_data.get("作品标题") or note_data.get("作品描述") or "无标题"
        base_dir = note_data.get("文件保存路径")
        filename = note_data.get("filename") or title

        if not base_dir or not os.path.isdir(base_dir):
            return {"ok": False, "error": "文件保存路径无效"}

        # 上传文件的辅助函数
        def upload_file(file_path: str, file_name: str) -> Optional[str]:
            """上传单个文件到飞书"""
            if not os.path.isfile(file_path):
                return None

            result = feishu.upload_file_to_bitable(
                file_path=file_path,
                file_name=file_name,
                parent_node=feishu.XHS_APP_TOKEN,
                parent_type="bitable_file",
                access_token=access_token,
            )

            if not result.get("success"):
                logger.warning(f"上传文件失败 {file_name}: {result.get('message')}")
                return None

            return result.get("file_token")

        # 上传封面
        cover_token = None
        note_type = note_data.get('作品类型')

        # 优先使用专门的封面文件
        cover_path = os.path.join(base_dir, "cover.jpg")
        if os.path.isfile(cover_path):
            cover_token = upload_file(cover_path, "cover.jpg")
        # 如果是图文类型且没有专门的封面，使用第一张图片作为封面
        elif note_type == '图文':
            first_image_path = os.path.join(base_dir, "image_0.jpg")
            if os.path.isfile(first_image_path):
                cover_token = upload_file(first_image_path, "image_0.jpg")
                logger.info("图文笔记：使用第一张图片作为封面")

        # 上传图片
        img_tokens = []
        if note_type == '图文':
            i = 0
            while True:
                img_path = os.path.join(base_dir, f"image_{i}.jpg")
                if not os.path.isfile(img_path):
                    break
                token = upload_file(img_path, f"image_{i}.jpg")
                if token:
                    img_tokens.append(token)
                i += 1

        # 上传视频
        video_token = None
        video_path = os.path.join(base_dir, "video.mp4")
        if os.path.isfile(video_path):
            video_token = upload_file(video_path, "video.mp4")

        # 组装飞书字段
        fields = {
            '标题': title,
            '笔记链接': note_data.get("作品链接") or "",
            '笔记ID': note_data.get("作品ID") or "",
            '作者': note_data.get("作者昵称") or "",
            '文案': note_data.get("作品描述") or "",
        }

        # 添加数值字段
        if note_data.get("点赞数量") is not None:
            fields['点赞数'] = str(note_data["点赞数量"])
        if note_data.get("评论数量") is not None:
            fields['评论数'] = str(note_data["评论数量"])
        if note_data.get("收藏数量") is not None:
            fields['收藏数'] = str(note_data["收藏数量"])

        # 添加时间字段
        publish_time_ts = parse_timestamp(note_data.get("发布时间"))
        if publish_time_ts:
            fields['发布时间'] = publish_time_ts

        last_edit_time_ts = parse_timestamp(note_data.get("最后更新时间"))
        if last_edit_time_ts:
            fields['最后编辑时间'] = last_edit_time_ts

        # 添加附件字段
        if cover_token:
            fields['封面'] = [{
                'file_token': cover_token,
                'name': f"{filename}_cover.jpg",
                'type': 'file',
            }]

        if video_token:
            fields['视频'] = [{
                'file_token': video_token,
                'name': f"{filename}.mp4",
                'type': 'file',
            }]

        if img_tokens:
            fields['图片'] = [
                {
                    'file_token': token,
                    'name': f"{filename}_{i}.jpg",
                    'type': 'file',
                }
                for i, token in enumerate(img_tokens)
            ]

        # 创建记录
        ok = feishu.create_xhs_record(fields, access_token=access_token)

        return {
            "ok": ok,
            "fields": fields,
            "message": "上传成功" if ok else "上传失败"
        }

    except Exception as e:
        logger.error(f"上传到飞书失败: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
