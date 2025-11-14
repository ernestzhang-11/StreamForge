"""
小红书作者信息解析工具
"""
import re
import requests
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# BeautifulSoup 是可选依赖
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("BeautifulSoup not available, using regex fallback")


def extract_user_id_from_url(url: str) -> Optional[str]:
    """
    从 URL 中提取用户 ID

    支持格式：
    - https://www.xiaohongshu.com/user/profile/68c3c849000000001901b11e?...
    - 短链接会在解析后变成上述格式

    Returns:
        用户ID（24位16进制字符串）
    """
    pattern = r'/user/profile/([a-f0-9]{24})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def extract_author_url_from_text(text: str) -> Optional[str]:
    """
    从文本中提取作者主页链接

    示例输入:
    "@跃轩听雨 在小红书收获了231次赞与收藏，查看Ta的主页>> https://xhslink.com/m/7lqHZ8ml6f"

    Returns:
        提取到的 URL
    """
    # 匹配 xiaohongshu.com 域名
    xhs_pattern = r'https?://(?:www\.)?xiaohongshu\.com/user/profile/[^\s]*'
    matches = re.findall(xhs_pattern, text)
    if matches:
        return matches[0].rstrip('.,;!?。，；！？')

    # 匹配短链接
    short_pattern = r'https?://xhslink\.com/[^\s]+'
    matches = re.findall(short_pattern, text)
    if matches:
        return matches[0].rstrip('.,;!?。，；！？')

    # 如果都没匹配到，可能本身就是 URL
    return text.strip()


def resolve_author_short_link(short_url: str, cookie: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    """
    解析作者短链接

    Args:
        short_url: 短链接
        cookie: 小红书 cookie
        timeout: 超时时间

    Returns:
        真实的用户主页链接
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
        }

        if cookie:
            headers['Cookie'] = cookie

        response = requests.get(
            short_url,
            headers=headers,
            allow_redirects=True,
            timeout=timeout
        )

        if response.history:
            final_url = response.url
            logger.info(f"作者短链接重定向: {short_url} -> {final_url}")
            return final_url

        return None
    except Exception as e:
        logger.error(f"解析作者短链接失败: {e}")
        return None


def fetch_author_page(url: str, cookie: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    """
    获取作者主页 HTML

    Args:
        url: 作者主页链接
        cookie: 小红书 cookie
        timeout: 超时时间

    Returns:
        HTML 内容
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        if cookie:
            headers['Cookie'] = cookie

        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        return response.text
    except Exception as e:
        logger.error(f"获取作者主页失败: {e}")
        return None


def parse_author_info_from_html(html: str) -> Dict[str, Any]:
    """
    从 HTML 中解析作者信息

    Args:
        html: 页面 HTML

    Returns:
        包含作者信息的字典：
        {
            "nickname": "昵称",
            "red_id": "小红书号",
            "ip_location": "IP属地",
            "fans_count": 粉丝数,
        }
    """
    try:
        result = {
            "nickname": None,
            "red_id": None,
            "ip_location": None,
            "fans_count": None,
        }

        # 方法1: 从页面 script 标签中的数据提取（通常是 window.__INITIAL_STATE__）
        # 使用正则直接匹配 script 内容，不依赖 BeautifulSoup
        script_pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL)
        scripts = script_pattern.findall(html)

        for script_content in scripts:
            if '__INITIAL_STATE__' in script_content:
                # 尝试提取 JSON 数据
                try:
                    import json
                    # 提取 JSON 部分
                    json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+\})\s*(?:</script>|$)', script_content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1).rstrip(';').strip()
                        # 替换 JavaScript 的 undefined 为 null
                        json_str = re.sub(r'\bundefined\b', 'null', json_str)
                        data = json.loads(json_str)

                        # 尝试从不同路径提取用户信息
                        user_data = None
                        if 'user' in data and 'userPageData' in data['user']:
                            user_data = data['user']['userPageData']
                        elif 'user' in data:
                            user_data = data['user']

                        if user_data:
                            # 从 basicInfo 提取基本信息
                            basic_info = user_data.get('basicInfo', {})
                            result['nickname'] = (basic_info.get('nickname') or
                                                 user_data.get('nickname'))
                            result['red_id'] = (basic_info.get('redId') or  # 注意是驼峰命名
                                               basic_info.get('red_id') or
                                               user_data.get('red_id'))
                            result['ip_location'] = (basic_info.get('ipLocation') or
                                                    basic_info.get('ip_location') or
                                                    user_data.get('ipLocation'))

                            # 粉丝数从 interactions 数组提取
                            interactions = user_data.get('interactions', [])
                            for interaction in interactions:
                                if interaction.get('type') == 'fans' or interaction.get('name') == '粉丝':
                                    fans_count = interaction.get('count')
                                    if fans_count:
                                        try:
                                            result['fans_count'] = int(fans_count)
                                        except (ValueError, TypeError):
                                            pass
                                    break

                            # 备用方案：从其他位置查找粉丝数
                            if result['fans_count'] is None:
                                fans = (user_data.get('fansCount') or
                                       basic_info.get('fansCount') or
                                       user_data.get('interactionInfo', {}).get('fansCount'))
                                if fans is not None:
                                    try:
                                        result['fans_count'] = int(fans)
                                    except (ValueError, TypeError):
                                        pass

                            logger.info(f"从 __INITIAL_STATE__ 提取到用户信息: {result}")
                            return result
                except Exception as e:
                    logger.debug(f"解析 __INITIAL_STATE__ 失败: {e}")

        # 方法2: 从 HTML 元素中提取（备用方案）
        # 昵称 - 多种方式提取
        if not result['nickname']:
            # 方式1: 从 class="user-name" 提取
            nickname_match = re.search(r'<div\s+class="user-name"[^>]*>([^<]+)</div>', html)
            if nickname_match:
                result['nickname'] = nickname_match.group(1).strip()
            else:
                # 方式2: 从 title 标签提取
                title_match = re.search(r'<title>([^<]+?)(?:的个人主页|个人主页)', html)
                if title_match:
                    result['nickname'] = title_match.group(1).strip()
                else:
                    # 方式3: 从 JSON 字符串中提取
                    nickname_match2 = re.search(r'"nickname"\s*:\s*"([^"]+)"', html)
                    if nickname_match2:
                        result['nickname'] = nickname_match2.group(1)

        # 小红书号
        if not result['red_id']:
            # 方式1: 从 user-redId class 提取（带中文标签）
            red_id_match = re.search(r'class="user-redId"[^>]*>小红书号[：:]\s*(\d+)</span>', html)
            if red_id_match:
                result['red_id'] = red_id_match.group(1)
            else:
                # 方式2: 纯正则匹配
                red_id_pattern = re.compile(r'小红书号[：:]\s*(\d+)')
                red_id_match2 = red_id_pattern.search(html)
                if red_id_match2:
                    result['red_id'] = red_id_match2.group(1)

        # IP属地
        if not result['ip_location']:
            ip_pattern = re.compile(r'IP属地[：:]\s*([^<\s]+)')
            ip_match = ip_pattern.search(html)
            if ip_match:
                result['ip_location'] = ip_match.group(1)

        # 粉丝数
        if result['fans_count'] is None:
            # 方式1: 从 user-interactions 提取（精确匹配）
            # <span class="count">15</span><span class="shows">粉丝</span>
            fans_match = re.search(r'<span class="count"[^>]*>(\d+)</span>\s*<span class="shows"[^>]*>粉丝</span>', html)
            if fans_match:
                result['fans_count'] = int(fans_match.group(1))
            else:
                # 方式2: "粉丝：123"
                fans_pattern = re.compile(r'粉丝[：:]\s*(\d+)')
                fans_match2 = fans_pattern.search(html)
                if fans_match2:
                    result['fans_count'] = int(fans_match2.group(1))
                else:
                    # 方式3: "123 粉丝"
                    fans_pattern2 = re.compile(r'(\d+)\s*粉丝')
                    fans_match3 = fans_pattern2.search(html)
                    if fans_match3:
                        result['fans_count'] = int(fans_match3.group(1))

        logger.info(f"从 HTML 元素提取到用户信息: {result}")
        return result

    except Exception as e:
        logger.error(f"解析作者信息失败: {e}")
        return {
            "nickname": None,
            "red_id": None,
            "ip_location": None,
            "fans_count": None,
        }


def parse_author(url: str, cookie: Optional[str] = None) -> Dict[str, Any]:
    """
    解析作者信息（主函数）

    Args:
        url: 作者主页链接或包含链接的文本
        cookie: 小红书 cookie

    Returns:
        {
            "ok": True/False,
            "data": {
                "user_id": "用户ID",
                "nickname": "昵称",
                "red_id": "小红书号",
                "ip_location": "IP属地",
                "fans_count": 粉丝数,
                "url": "标准化的用户主页链接"
            },
            "error": "错误信息（如果有）"
        }
    """
    try:
        # 1. 提取 URL
        extracted_url = extract_author_url_from_text(url)
        if not extracted_url:
            return {"ok": False, "error": "无法从输入文本中提取URL"}

        logger.info(f"提取到URL: {extracted_url}")

        # 保存原始 URL 用于提取 xsec_token
        original_url = extracted_url

        # 2. 检查是否为短链接
        if 'xhslink.com' in extracted_url:
            logger.info(f"检测到作者短链接: {extracted_url}")
            extracted_url = resolve_author_short_link(extracted_url, cookie)
            if not extracted_url:
                return {"ok": False, "error": "短链接解析失败"}
            logger.info(f"短链接解析结果: {extracted_url}")
            # 短链接解析后的 URL 作为原始 URL
            original_url = extracted_url

        # 3. 提取用户 ID
        user_id = extract_user_id_from_url(extracted_url)
        if not user_id:
            return {"ok": False, "error": "无法从URL中提取用户ID"}

        logger.info(f"提取到用户ID: {user_id}")

        # 4. 从原始 URL 中提取 xsec_token（如果有）
        xsec_token = None
        if 'xsec_token=' in original_url:
            import re
            token_match = re.search(r'xsec_token=([^&\s]+)', original_url)
            if token_match:
                xsec_token = token_match.group(1)
                logger.info(f"提取到 xsec_token: {xsec_token[:20]}...")

        # 5. 获取页面 HTML
        html = fetch_author_page(extracted_url, cookie)
        if not html:
            return {"ok": False, "error": "无法获取作者主页"}

        # 6. 解析作者信息
        author_info = parse_author_info_from_html(html)

        # 7. 拼接主页链接
        if xsec_token:
            profile_url = f"https://www.xiaohongshu.com/user/profile/{user_id}?xsec_token={xsec_token}"
        else:
            profile_url = f"https://www.xiaohongshu.com/user/profile/{user_id}"

        # 8. 组装结果
        result = {
            "ok": True,
            "data": {
                "user_id": user_id,
                "nickname": author_info.get("nickname"),
                "red_id": author_info.get("red_id"),
                "ip_location": author_info.get("ip_location"),
                "fans_count": author_info.get("fans_count"),
                "url": f"https://www.xiaohongshu.com/user/profile/{user_id}",
                "profile_url": profile_url,  # 主页链接（带或不带 xsec_token）
                "xsec_token": xsec_token  # xsec_token（可能为 None）
            }
        }

        return result

    except Exception as e:
        logger.error(f"解析作者信息失败: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
