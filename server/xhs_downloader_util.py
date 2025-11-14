"""
小红书笔记统一下载工具
适配 API 模式和 Web 模式的数据结构，统一下载逻辑
"""
import os
import re
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from retry import retry

logger = logging.getLogger(__name__)


def norm_str(text: str) -> str:
    """
    标准化字符串，移除文件名中的非法字符
    """
    if not text:
        return ""
    # 移除文件系统不允许的字符
    new_str = re.sub(r'[\\/:*?"<>|]+', "", text)
    # 移除换行符
    new_str = new_str.replace('\n', '').replace('\r', '')
    return new_str.strip()


def normalize_note_data(data: Dict[str, Any], mode: str = "api") -> Dict[str, Any]:
    """
    标准化笔记数据结构（API模式和Web模式）

    Args:
        data: 原始笔记数据
        mode: "api" 或 "web"

    Returns:
        标准化后的数据结构
    """
    if mode == "api":
        # API 模式的数据结构
        return {
            "note_id": data.get("作品ID") or "",
            "note_url": data.get("作品链接") or "",
            "note_type": data.get("作品类型") or "",  # "图文" 或 "视频"
            "user_id": "",  # API 模式可能没有 user_id
            "nickname": data.get("作者昵称") or "未知作者",
            "title": data.get("作品标题") or data.get("作品描述") or "无标题",
            "desc": data.get("作品描述") or "",
            "liked_count": data.get("点赞数量") or 0,
            "collected_count": data.get("收藏数量") or 0,
            "comment_count": data.get("评论数量") or 0,
            "video_cover": data.get("视频封面url"),
            "video_addr": data.get("视频地址url"),
            "image_list": data.get("下载地址") or [],
            "upload_time": data.get("发布时间") or "",
        }
    else:
        # Web 模式的数据结构（已经是标准化的）
        return {
            "note_id": data.get("作品ID") or "",
            "note_url": data.get("作品链接") or "",
            "note_type": data.get("作品类型") or "",
            "user_id": "",
            "nickname": data.get("作者昵称") or "未知作者",
            "title": data.get("作品标题") or data.get("作品描述") or "无标题",
            "desc": data.get("作品描述") or "",
            "liked_count": data.get("点赞数量") or 0,
            "collected_count": data.get("收藏数量") or 0,
            "comment_count": data.get("评论数量") or 0,
            "video_cover": None,
            "video_addr": None,
            "image_list": data.get("下载地址") or [],
            "upload_time": data.get("发布时间") or "",
        }


def check_and_create_path(path: str) -> None:
    """
    检查并创建目录
    """
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"创建目录: {path}")


@retry(tries=3, delay=1)
def download_media(save_path: str, filename: str, url: str, media_type: str) -> bool:
    """
    下载媒体文件（图片或视频）

    Args:
        save_path: 保存目录
        filename: 文件名（不含扩展名）
        url: 下载URL
        media_type: "image" 或 "video"

    Returns:
        是否下载成功
    """
    try:
        if media_type == "image":
            extension = ".jpg"
            chunk_size = 1024 * 1024  # 1MB
        else:  # video
            extension = ".mp4"
            chunk_size = 1024 * 1024 * 10  # 10MB

        file_path = os.path.join(save_path, f"{filename}{extension}")

        # 如果文件已存在，跳过下载
        if os.path.exists(file_path):
            logger.info(f"文件已存在，跳过下载: {file_path}")
            return True

        # 下载文件
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = 0
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)

        logger.info(f"下载成功: {file_path} ({total_size / 1024 / 1024:.2f}MB)")
        return True

    except Exception as e:
        logger.error(f"下载失败 {url}: {e}")
        # 删除不完整的文件
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        return False


def save_note_metadata(note_data: Dict[str, Any], save_path: str) -> None:
    """
    保存笔记元数据到 JSON 和 TXT 文件
    """
    # 保存 JSON
    json_path = os.path.join(save_path, "info.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(note_data, f, ensure_ascii=False, indent=2)

    # 保存可读的 TXT
    txt_path = os.path.join(save_path, "detail.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"笔记ID: {note_data.get('note_id')}\n")
        f.write(f"笔记URL: {note_data.get('note_url')}\n")
        f.write(f"笔记类型: {note_data.get('note_type')}\n")
        f.write(f"作者昵称: {note_data.get('nickname')}\n")
        f.write(f"标题: {note_data.get('title')}\n")
        f.write(f"描述: {note_data.get('desc')}\n")
        f.write(f"点赞数量: {note_data.get('liked_count')}\n")
        f.write(f"收藏数量: {note_data.get('collected_count')}\n")
        f.write(f"评论数量: {note_data.get('comment_count')}\n")
        f.write(f"上传时间: {note_data.get('upload_time')}\n")
        if note_data.get('note_type') == '视频':
            f.write(f"视频封面URL: {note_data.get('video_cover')}\n")
            f.write(f"视频地址URL: {note_data.get('video_addr')}\n")
        else:
            f.write(f"图片数量: {len(note_data.get('image_list', []))}\n")

    logger.info(f"元数据已保存: {save_path}")


def download_note(
    note_data: Dict[str, Any],
    base_path: str,
    mode: str = "api",
    download_images: bool = True,
    download_videos: bool = True
) -> Optional[str]:
    """
    统一的笔记下载方法，支持 API 和 Web 模式

    Args:
        note_data: 笔记数据（API模式或Web模式）
        base_path: 基础保存路径
        mode: "api" 或 "web"
        download_images: 是否下载图片
        download_videos: 是否下载视频

    Returns:
        保存路径，失败返回 None
    """
    try:
        # 标准化数据结构
        normalized = normalize_note_data(note_data, mode)

        note_id = normalized["note_id"]
        nickname = normalized["nickname"]
        title = normalized["title"]
        note_type = normalized["note_type"]

        # 标准化文件名（限制长度）
        safe_nickname = norm_str(nickname)[:20]
        safe_title = norm_str(title)[:40]

        if not safe_title:
            safe_title = "无标题"

        # 构建保存路径：{base_path}/{nickname}/{title}_{note_id}
        # 这样可以避免不同笔记的文件互相覆盖
        save_path = os.path.join(
            base_path,
            safe_nickname,
            f"{safe_title}_{note_id}"
        )

        # 创建目录
        check_and_create_path(save_path)

        # 保存元数据
        save_note_metadata(normalized, save_path)

        # 根据笔记类型下载媒体文件
        if note_type == "图文" and download_images:
            image_list = normalized.get("image_list") or []
            logger.info(f"开始下载图片，共 {len(image_list)} 张")

            for img_index, img_url in enumerate(image_list):
                if img_url:
                    success = download_media(
                        save_path,
                        f"image_{img_index}",
                        img_url,
                        "image"
                    )
                    if not success:
                        logger.warning(f"图片 {img_index} 下载失败")

        elif note_type == "视频" and download_videos:
            logger.info("开始下载视频")

            # 下载视频封面
            video_cover = normalized.get("video_cover")
            if video_cover:
                download_media(save_path, "cover", video_cover, "image")

            # 下载视频
            video_addr = normalized.get("video_addr")
            if video_addr:
                success = download_media(save_path, "video", video_addr, "video")
                if not success:
                    logger.error("视频下载失败")
                    return None

        logger.info(f"笔记下载完成: {save_path}")
        return save_path

    except Exception as e:
        logger.error(f"下载笔记失败: {e}", exc_info=True)
        return None


def batch_download_notes(
    notes_data: List[Dict[str, Any]],
    base_path: str,
    mode: str = "api",
    download_images: bool = True,
    download_videos: bool = True
) -> Dict[str, Any]:
    """
    批量下载笔记

    Args:
        notes_data: 笔记数据列表
        base_path: 基础保存路径
        mode: "api" 或 "web"
        download_images: 是否下载图片
        download_videos: 是否下载视频

    Returns:
        下载统计信息
    """
    total = len(notes_data)
    success_count = 0
    failed_count = 0
    saved_paths = []

    logger.info(f"开始批量下载 {total} 个笔记")

    for idx, note_data in enumerate(notes_data, 1):
        logger.info(f"处理第 {idx}/{total} 个笔记")

        save_path = download_note(
            note_data,
            base_path,
            mode=mode,
            download_images=download_images,
            download_videos=download_videos
        )

        if save_path:
            success_count += 1
            saved_paths.append(save_path)
        else:
            failed_count += 1

    result = {
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "saved_paths": saved_paths
    }

    logger.info(f"批量下载完成: 成功 {success_count}/{total}，失败 {failed_count}")
    return result


if __name__ == "__main__":
    # 测试用例
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # 模拟 API 模式的数据
    test_note_api = {
        "作品标题": "测试笔记标题",
        "作品描述": "这是一个测试描述",
        "作品链接": "https://www.xiaohongshu.com/explore/test123",
        "作品ID": "test123456789012345678",
        "作者昵称": "测试作者",
        "作品类型": "图文",
        "下载地址": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
        ],
    }

    print("测试数据标准化:")
    normalized = normalize_note_data(test_note_api, mode="api")
    print(json.dumps(normalized, ensure_ascii=False, indent=2))

    print("\n测试文件名标准化:")
    print(f"原始: '测试/标题:带*非法?字符'")
    print(f"标准化: '{norm_str('测试/标题:带*非法?字符')}'")
