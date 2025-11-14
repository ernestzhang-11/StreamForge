"""
小红书商品信息解析工具
"""
import re
import requests
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def extract_goods_url_from_text(text: str) -> Optional[str]:
    """
    从文本中提取商品链接

    示例输入:
    "【小红书】朱砂莲花貔貅挂件 😆 4jIpmS2A05S 😆 https://xhslink.com/m/1iQ4klmficO 点击链接..."

    Returns:
        提取到的 URL
    """
    # 匹配 xiaohongshu.com 域名
    xhs_pattern = r'https?://(?:www\.)?xiaohongshu\.com/goods-detail/[^\s]*'
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


def resolve_goods_short_link(short_url: str, cookie: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    """
    解析商品短链接

    Args:
        short_url: 短链接
        cookie: 小红书 cookie
        timeout: 超时时间

    Returns:
        真实的商品详情链接
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
            logger.info(f"商品短链接重定向: {short_url} -> {final_url}")
            return final_url

        return None
    except Exception as e:
        logger.error(f"解析商品短链接失败: {e}")
        return None


def extract_goods_id_from_url(url: str) -> Optional[str]:
    """
    从 URL 中提取商品 ID

    支持格式：
    - https://www.xiaohongshu.com/goods-detail/68bf7e9b6a569a0015b68337?xsec_token=...

    Returns:
        商品ID（24位16进制字符串）
    """
    pattern = r'/goods-detail/([a-f0-9]{24})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def fetch_goods_detail(goods_id: str, cookie: Optional[str] = None, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    获取商品详情

    Args:
        goods_id: 商品ID
        cookie: 小红书 cookie
        timeout: 超时时间

    Returns:
        商品详情 JSON 数据
    """
    try:
        url = f"https://mall.xiaohongshu.com/api/store/jpd/edith/detail/h5/toc?version=0.0.5&item_id={goods_id}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
            'Accept': 'application/json',
        }

        if cookie:
            headers['Cookie'] = cookie

        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        logger.info(f"成功获取商品详情: {goods_id}")
        return data
    except Exception as e:
        logger.error(f"获取商品详情失败: {e}")
        return None


def parse_goods_info(goods_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 API 响应中解析商品信息

    Args:
        goods_data: 商品详情 API 响应

    Returns:
        {
            "title": "商品标题",
            "shop_name": "店铺名称",
            "price": "商品价格",
            "sales_volume": "已售数量",
            "seller_user_id": "卖家用户ID",
            "image_url": "商品图片URL"
        }
    """
    try:
        result = {
            "title": None,
            "shop_name": None,
            "price": None,
            "sales_volume": None,
            "seller_user_id": None,
            "image_url": None,
        }

        # 检查响应格式
        if 'data' not in goods_data:
            logger.warning("响应中没有 data 字段")
            return result

        data = goods_data['data']

        # 从 template_data[0] 提取信息
        if 'template_data' in data and isinstance(data['template_data'], list) and len(data['template_data']) > 0:
            template_data = data['template_data'][0]

            # 从 descriptionH5 提取商品标题
            if 'descriptionH5' in template_data:
                desc = template_data['descriptionH5']
                result['title'] = desc.get('name')

            # 从 priceH5 提取价格和销量
            if 'priceH5' in template_data:
                price_info = template_data['priceH5']

                # 优先使用 dealPrice，其次 highlightPrice
                if 'dealPrice' in price_info and price_info['dealPrice']:
                    result['price'] = price_info['dealPrice'].get('price')
                elif 'highlightPrice' in price_info:
                    result['price'] = price_info['highlightPrice']

                # 销量从 itemAnalysisDataText 提取（格式："已售3093"）
                sales_text = price_info.get('itemAnalysisDataText')
                if sales_text:
                    # 提取数字
                    import re
                    sales_match = re.search(r'已售(\d+)', sales_text)
                    if sales_match:
                        result['sales_volume'] = int(sales_match.group(1))

            # 从 sellerH5 提取店铺信息和卖家ID
            if 'sellerH5' in template_data:
                seller = template_data['sellerH5']
                result['shop_name'] = seller.get('name')
                # 暂时不从这里获取 seller_user_id，优先使用 profitBarPopupH5

                # 如果没有从 priceH5 获取到销量，尝试从这里获取
                if result['sales_volume'] is None and 'salesVolume' in seller:
                    sales_text = seller.get('salesVolume')
                    if sales_text:
                        sales_match = re.search(r'已售(\d+)', sales_text)
                        if sales_match:
                            result['sales_volume'] = int(sales_match.group(1))

            # 优先从 profitBarPopupH5.follow.sellerUserId 获取卖家用户ID
            if 'profitBarPopupH5' in template_data:
                profit_bar = template_data['profitBarPopupH5']
                if 'follow' in profit_bar:
                    follow = profit_bar['follow']
                    result['seller_user_id'] = follow.get('sellerUserId')
                    # 如果 shop_name 还没有，也可以从这里获取
                    if not result['shop_name']:
                        result['shop_name'] = follow.get('name')

            # 备用方案1：从 sellerH5 提取卖家ID
            if not result['seller_user_id'] and 'sellerH5' in template_data:
                seller = template_data['sellerH5']
                result['seller_user_id'] = seller.get('id')

            # 备用方案2：从 bottomBarMainH5 提取卖家ID
            if not result['seller_user_id'] and 'bottomBarMainH5' in template_data:
                bottom_bar = template_data['bottomBarMainH5']
                if 'seller' in bottom_bar:
                    result['seller_user_id'] = bottom_bar['seller'].get('sellerId')

        # 从 headerBarMainPopup 中提取图片URL
        if 'headerBarMainPopup' in template_data:
            popup = template_data['headerBarMainPopup']
            if isinstance(popup, dict) and 'list' in popup:
                popup_list = popup['list']
                if isinstance(popup_list, list):
                    # 查找名称为"分享"的项
                    for item in popup_list:
                        if isinstance(item, dict) and item.get('name') == '分享':
                            if 'data' in item and isinstance(item['data'], dict):
                                if 'shareData' in item['data']:
                                    share_data = item['data']['shareData']
                                    result['image_url'] = share_data.get('imageurl') or share_data.get('image')
                                    logger.info(f"从 headerBarMainPopup 提取到图片URL: {result['image_url'][:60]}...")
                                    break

        logger.info(f"解析商品信息: {result}")
        return result

    except Exception as e:
        logger.error(f"解析商品信息失败: {e}", exc_info=True)
        return {
            "title": None,
            "shop_name": None,
            "price": None,
            "sales_volume": None,
            "seller_user_id": None,
            "image_url": None,
        }


def download_goods_image(image_url: str, goods_id: str, download_dir: str = "downloads/goods") -> Optional[str]:
    """
    下载商品图片

    Args:
        image_url: 图片URL
        goods_id: 商品ID
        download_dir: 下载目录

    Returns:
        下载后的本地文件路径
    """
    try:
        import os
        from urllib.parse import urlparse

        # 创建下载目录
        os.makedirs(download_dir, exist_ok=True)

        # 从 URL 提取文件扩展名
        parsed_url = urlparse(image_url)
        ext = ".jpg"  # 默认扩展名
        if '.' in parsed_url.path:
            ext = os.path.splitext(parsed_url.path)[1].split('?')[0] or ".jpg"

        # 生成文件名
        file_name = f"{goods_id}{ext}"
        file_path = os.path.join(download_dir, file_name)

        # 下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
        }

        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()

        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"成功下载商品图片: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"下载商品图片失败: {e}")
        return None


def parse_goods(url: str, cookie: Optional[str] = None) -> Dict[str, Any]:
    """
    解析商品信息（主函数）

    Args:
        url: 商品链接或包含链接的文本
        cookie: 小红书 cookie

    Returns:
        {
            "ok": True/False,
            "data": {
                "goods_id": "商品ID",
                "title": "商品标题",
                "shop_name": "店铺名称",
                "price": "商品价格",
                "sales_volume": "已售数量",
                "goods_url": "商品链接（带 xsec_token）",
                "seller_profile_url": "卖家主页链接"
            },
            "error": "错误信息（如果有）"
        }
    """
    try:
        # 1. 提取 URL
        extracted_url = extract_goods_url_from_text(url)
        if not extracted_url:
            return {"ok": False, "error": "无法从输入文本中提取URL"}

        logger.info(f"提取到商品URL: {extracted_url}")

        # 保存原始 URL
        original_url = extracted_url

        # 2. 检查是否为短链接
        if 'xhslink.com' in extracted_url:
            logger.info(f"检测到商品短链接: {extracted_url}")
            extracted_url = resolve_goods_short_link(extracted_url, cookie)
            if not extracted_url:
                return {"ok": False, "error": "短链接解析失败"}
            logger.info(f"短链接解析结果: {extracted_url}")
            original_url = extracted_url

        # 3. 提取商品 ID
        goods_id = extract_goods_id_from_url(extracted_url)
        if not goods_id:
            return {"ok": False, "error": "无法从URL中提取商品ID"}

        logger.info(f"提取到商品ID: {goods_id}")

        # 4. 从原始 URL 中提取 xsec_token
        xsec_token = None
        if 'xsec_token=' in original_url:
            token_match = re.search(r'xsec_token=([^&\s]+)', original_url)
            if token_match:
                xsec_token = token_match.group(1)
                logger.info(f"提取到 xsec_token: {xsec_token[:20]}...")

        # 5. 拼接商品链接
        if xsec_token:
            goods_url = f"https://www.xiaohongshu.com/goods-detail/{goods_id}?xsec_token={xsec_token}"
        else:
            goods_url = f"https://www.xiaohongshu.com/goods-detail/{goods_id}"

        # 6. 获取商品详情
        goods_data = fetch_goods_detail(goods_id, cookie)
        if not goods_data:
            return {"ok": False, "error": "无法获取商品详情"}

        # 7. 解析商品信息
        goods_info = parse_goods_info(goods_data)

        # 8. 下载商品图片（如果有）
        image_path = None
        if goods_info.get('image_url'):
            image_path = download_goods_image(goods_info['image_url'], goods_id)
            if image_path:
                logger.info(f"商品图片已下载: {image_path}")

        # 9. 拼接卖家主页链接
        seller_profile_url = None
        if goods_info.get('seller_user_id'):
            seller_profile_url = f"https://www.xiaohongshu.com/user/profile/{goods_info['seller_user_id']}"

        # 10. 组装结果
        result = {
            "ok": True,
            "data": {
                "goods_id": goods_id,
                "title": goods_info.get("title"),
                "shop_name": goods_info.get("shop_name"),
                "price": goods_info.get("price"),
                "sales_volume": goods_info.get("sales_volume"),
                "goods_url": goods_url,
                "seller_profile_url": seller_profile_url,
                "image_url": goods_info.get("image_url"),
                "image_path": image_path  # 本地图片路径
            }
        }

        return result

    except Exception as e:
        logger.error(f"解析商品信息失败: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
