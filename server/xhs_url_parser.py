"""
小红书链接解析工具
支持多种格式的链接解析，统一转换为标准格式
"""
import re
import requests
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)


def extract_note_info_from_url(url: str, cookie: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    从小红书链接中提取笔记ID和xsec_token

    支持的格式：
    1. 短链接: http://xhslink.com/o/xxxxx
    2. discovery链接: https://www.xiaohongshu.com/discovery/item/{note_id}?xsec_token=xxx
    3. explore链接: https://www.xiaohongshu.com/explore/{note_id}?xsec_token=xxx
    4. 登录重定向: https://www.xiaohongshu.com/login?redirectPath=https://www.xiaohongshu.com/discovery/item/{note_id}?...

    Args:
        url: 原始URL（可能包含在文本中）
        cookie: 小红书cookie（用于解析短链接）

    Returns:
        (note_id, xsec_token, normalized_url)
    """
    if not url:
        return None, None, None

    # 提取URL（从文本中）
    url = extract_url_from_text(url)
    if not url:
        logger.warning("无法从输入文本中提取URL")
        return None, None, None

    # 检查是否为短链接
    if is_short_link(url):
        logger.info(f"检测到短链接: {url}")
        url = resolve_short_link(url, cookie)
        if not url:
            logger.error("短链接解析失败")
            return None, None, None
        logger.info(f"短链接解析结果: {url}")

    # 检查是否为登录重定向URL（短链接可能重定向到登录页）
    if '/login' in url and 'redirectPath=' in url:
        logger.info(f"检测到登录重定向URL")
        redirect_url = extract_redirect_path(url)
        if redirect_url:
            logger.info(f"从 redirectPath 提取到目标URL")
            url = redirect_url
        else:
            logger.warning("无法从登录重定向URL中提取 redirectPath")

    # 提取笔记ID
    note_id = extract_note_id(url)
    if not note_id:
        logger.warning(f"无法从URL中提取笔记ID: {url}")
        return None, None, None

    # 提取xsec_token
    xsec_token = extract_xsec_token(url)
    if not xsec_token:
        logger.warning(f"无法从URL中提取xsec_token: {url}")
        return None, None, None

    # 生成标准化URL
    normalized_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}"

    return note_id, xsec_token, normalized_url


def extract_url_from_text(text: str) -> Optional[str]:
    """
    从文本中提取URL

    示例输入:
    "对方保险公司要我们赔5w 对方车损一个灯罩，掉漆，还... http://xhslink.com/o/9GubyGk1LPj"
    "63%20【标题】 😆 https://www.xiaohongshu.com/discovery/item/xxx?xsec_token=xxx"

    Returns:
        提取到的URL
    """
    # 先解码 URL 编码（如果有的话）
    import urllib.parse
    try:
        decoded_text = urllib.parse.unquote(text)
    except Exception:
        decoded_text = text

    # 匹配 xiaohongshu.com 域名的完整URL（优先）
    # 这个模式会匹配从 http/https 开始，到下一个空格、中文或字符串结尾
    xhs_pattern = r'https?://(?:www\.)?xiaohongshu\.com/[^\s\u4e00-\u9fff]*'
    xhs_matches = re.findall(xhs_pattern, decoded_text)

    if xhs_matches:
        # 清理 URL 末尾可能的标点符号
        url = xhs_matches[0].rstrip('.,;!?。，；！？')
        return url

    # 匹配短链接或其他 http/https 链接
    url_pattern = r'https?://[^\s\u4e00-\u9fff]+'
    matches = re.findall(url_pattern, decoded_text)

    if matches:
        # 清理 URL 末尾可能的标点符号
        url = matches[0].rstrip('.,;!?。，；！？')
        return url

    # 如果没有找到URL，返回原始文本（可能本身就是URL）
    return text.strip()


def extract_redirect_path(url: str) -> Optional[str]:
    """
    从登录重定向URL中提取redirectPath参数

    示例输入:
    https://www.xiaohongshu.com/login?redirectPath=https://www.xiaohongshu.com/discovery/item/xxx?xsec_token=yyy

    Returns:
        提取到的redirectPath URL
    """
    try:
        # 使用正则表达式提取 redirectPath，因为它的值本身就是一个完整的 URL
        # 直接用 parse_qs 会把内嵌 URL 的参数也拆分出来
        redirect_match = re.search(r'redirectPath=([^&\s]+(?:&[^&\s]+)*)', url)
        if redirect_match:
            # 获取 redirectPath 后面的所有内容，直到遇到不属于 URL 的字符
            redirect_start = redirect_match.start(1)
            # 从 redirectPath 的值开始，一直到字符串结尾或空格
            remaining = url[redirect_start:]

            # redirectPath 的值应该是从 https:// 开始的完整 URL
            # 我们需要找到它的结束位置
            # 结束标志：空格、引号、或者字符串结尾
            redirect_url = remaining.split()[0].rstrip('",;')

            # URL 解码（redirectPath 的值可能是编码的，如 %3A %2F）
            import urllib.parse
            try:
                decoded_url = urllib.parse.unquote(redirect_url)
                logger.info(f"从redirectPath提取URL（已解码）: {decoded_url[:100]}...")
                return decoded_url
            except Exception:
                logger.info(f"从redirectPath提取URL: {redirect_url[:100]}...")
                return redirect_url

        # 如果正则匹配失败，尝试传统方法
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        if 'redirectPath' in query_params:
            # parse_qs 会拆分内嵌的参数，我们需要重新组装
            # 注意：parse_qs 会自动解码，所以 base_redirect 已经是解码后的
            base_redirect = query_params['redirectPath'][0]

            # 收集所有可能属于 redirectPath 的参数
            redirect_params = {}
            for key in ['app_platform', 'app_version', 'share_from_user_hidden',
                       'xsec_source', 'type', 'xsec_token', 'author_share',
                       'xhsshare', 'shareRedId', 'apptime', 'share_id', 'exSource']:
                if key in query_params:
                    redirect_params[key] = query_params[key][0]

            # 重新组装 redirectPath
            if redirect_params:
                params_list = [f"{k}={v}" for k, v in redirect_params.items()]
                param_str = '&'.join(params_list)
                redirect_url = base_redirect + '&' + param_str
                logger.info(f"重新组装redirectPath（已解码）: {redirect_url[:100]}...")
                return redirect_url
            else:
                logger.info(f"提取redirectPath（已解码）: {base_redirect[:100]}...")
                return base_redirect

        return None
    except Exception as e:
        logger.error(f"提取redirectPath失败: {e}")
        return None


def is_short_link(url: str) -> bool:
    """
    判断是否为小红书短链接
    """
    return 'xhslink.com' in url.lower()


def resolve_short_link(short_url: str, cookie: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    """
    解析小红书短链接，获取真实的长链接

    Args:
        short_url: 短链接 (如: http://xhslink.com/o/9GubyGk1LPj)
        cookie: 小红书cookie
        timeout: 请求超时时间（秒）

    Returns:
        真实的长链接
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
        }

        if cookie:
            headers['Cookie'] = cookie

        # 发送请求，不自动跟随重定向
        response = requests.get(
            short_url,
            headers=headers,
            allow_redirects=True,  # 自动跟随重定向
            timeout=timeout
        )

        # 如果发生了重定向，返回最终URL
        if response.history:
            final_url = response.url
            logger.info(f"短链接重定向: {short_url} -> {final_url}")
            return final_url

        # 如果没有重定向，检查响应体中是否包含链接
        if response.status_code == 200:
            # 尝试从响应中提取链接
            text = response.text
            url_match = re.search(r'https://www\.xiaohongshu\.com/[^\s"\'<>]+', text)
            if url_match:
                return url_match.group(0)

        logger.warning(f"短链接解析失败，状态码: {response.status_code}")
        return None

    except requests.exceptions.Timeout:
        logger.error(f"短链接请求超时: {short_url}")
        return None
    except Exception as e:
        logger.error(f"短链接解析异常: {e}")
        return None


def extract_note_id(url: str) -> Optional[str]:
    """
    从URL中提取笔记ID

    支持的格式：
    - https://www.xiaohongshu.com/explore/{note_id}
    - https://www.xiaohongshu.com/discovery/item/{note_id}
    """
    # 尝试从explore路径提取
    explore_pattern = r'/explore/([a-f0-9]{24})'
    match = re.search(explore_pattern, url)
    if match:
        return match.group(1)

    # 尝试从discovery/item路径提取
    discovery_pattern = r'/discovery/item/([a-f0-9]{24})'
    match = re.search(discovery_pattern, url)
    if match:
        return match.group(1)

    return None


def extract_xsec_token(url: str) -> Optional[str]:
    """
    从URL查询参数中提取xsec_token
    """
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        # 获取xsec_token参数
        if 'xsec_token' in query_params:
            tokens = query_params['xsec_token']
            if tokens and len(tokens) > 0:
                return tokens[0]

        return None
    except Exception as e:
        logger.error(f"提取xsec_token失败: {e}")
        return None


def normalize_xhs_url(input_text: str, cookie: Optional[str] = None) -> Optional[str]:
    """
    便捷方法：标准化小红书链接

    Args:
        input_text: 输入文本（可能包含链接）
        cookie: 小红书cookie

    Returns:
        标准化的URL: https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}
    """
    note_id, xsec_token, normalized_url = extract_note_info_from_url(input_text, cookie)
    return normalized_url


if __name__ == "__main__":
    # 测试用例
    import sys
    import io

    # 修复Windows控制台编码问题
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # 测试用例1: 短链接
    test_url_1 = "对方保险公司要我们赔5w 对方车损一个灯罩，掉漆，还... http://xhslink.com/o/9GubyGk1LPj 复制后打开【小红书】查看笔记！"
    logger.info(f"测试1 输入: {test_url_1}")
    # 需要cookie才能解析短链接
    # result_1 = normalize_xhs_url(test_url_1, cookie='your_cookie_here')
    # logger.info(f"测试1 结果: {result_1}\n")

    # 测试用例2: discovery链接
    test_url_2 = "https://www.xiaohongshu.com/discovery/item/691640ea0000000007022395?source=webshare&xhsshare=pc_web&xsec_token=CBr0pTTp8vm5CarMUCnZfuPTHwVMNXGXjnvPvI9NvsgqQ=&xsec_source=pc_share"
    logger.info(f"测试2 输入: {test_url_2}")
    result_2 = normalize_xhs_url(test_url_2)
    logger.info(f"测试2 结果: {result_2}\n")

    # 测试用例3: explore链接
    test_url_3 = "https://www.xiaohongshu.com/explore/691640ea0000000007022395?app_platform=ios&app_version=9.6&share_from_user_hidden=true&xsec_source=app_share&type=normal&xsec_token=CBr0pTTp8vm5CarMUCnZfuPTHwVMNXGXjnvPvI9NvsgqQ=&author_share=1&xhsshare=CopyLink&shareRedId=ODk5RjU3RU42NzUyOTgwNjdJOTg6Rz1B&apptime=1763089039&share_id=0840e2340e9d421597831a18b2c2acbb"
    logger.info(f"测试3 输入: {test_url_3}")
    result_3 = normalize_xhs_url(test_url_3)
    logger.info(f"测试3 结果: {result_3}\n")
