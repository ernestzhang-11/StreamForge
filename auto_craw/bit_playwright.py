from bit_api import openBrowser, closeBrowser
import asyncio
import re
import os
import time
import json
import traceback
from typing import List, Dict
from urllib.parse import quote
from playwright.async_api import async_playwright, Playwright, Browser, Page
import requests
from datetime import datetime


BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:5000")
BIT_BROWSER_ID = os.getenv("BIT_BROWSER_ID", "6b130d1cdcb3485897b9ca81aefb1a66")
MAX_VIDEOS = int(os.getenv("MAX_VIDEOS", "200"))
RECENT_DAYS = int(os.getenv("RECENT_DAYS", "3"))
KEYWORDS_FILE = os.getenv("KEYWORDS_FILE", os.path.join(os.path.dirname(__file__), "keywords.txt"))
UPLOADED_URLS_FILE = os.getenv("UPLOADED_URLS_FILE", os.path.join(os.path.dirname(__file__), "uploaded_urls.txt"))
FAILED_URLS_FILE = os.getenv("FAILED_URLS_FILE", os.path.join(os.path.dirname(__file__), "failed_urls.txt"))

VIDEO_HREF_RE = re.compile(r"/video/\d+")

async def open_bit_browser(playwright: Playwright, browser_id: str) -> tuple[Browser, Page]:
    res = openBrowser(browser_id)
    ws = res["data"]["ws"]
    chromium = playwright.chromium
    browser = await chromium.connect_over_cdp(ws)
    ctx = browser.contexts[0]
    page = await ctx.new_page()
    return browser, page

async def goto_douyin_search(page: Page, keyword: str):
    # 使用通用搜索 type=general
    url = f"https://www.douyin.com/search/{quote(keyword)}?type=general"
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)

async def apply_latest_filter(page: Page):
    # 抖音搜索页通常有排序/筛选。尝试点击“最新”/“最新发布”等关键词
    candidates = ["最新", "最新发布", "按时间", "时间"]
    for text in candidates:
        try:
            el = page.get_by_text(text, exact=False)
            await el.first.click(timeout=1500)
            await page.wait_for_timeout(800)
            break
        except Exception:
            continue

async def collect_video_links_via_xhr(page: Page, limit: int, timeout_ms: int = 15000) -> List[str]:
    """监听网络响应，抓取 URL 中包含 'search' 的 XHR/Fetch 返回体，提取 aweme_id 和 create_time，筛选最近 N 天，并生成视频链接。
    额外：对首条命中的 search/stream(fetch) 使用页面层 8 秒缓冲后一次性快照。
    """
    collected: dict[str, int] = {}  # url -> create_time
    done = asyncio.Event()

    cutoff = int(time.time()) - RECENT_DAYS * 24 * 3600

    async def on_response(resp):
        try:
            req = resp.request
            rt = getattr(req, "resource_type", "") or ""
            if rt not in ("xhr", "fetch"):
                return
            url = resp.url or ""
            if ("search/single" not in url and "search/item" not in url):
                return

            ctype = resp.headers.get("content-type", "")
            if "application/json" not in ctype and "json" not in ctype:
                return


            # 非流式 JSON 的常规解析路径
            text = await resp.text()
            data = json.loads(text)
            items: list[dict] = []

            def walk(o):
                if isinstance(o, dict):
                    if "aweme_info" in o and isinstance(o["aweme_info"], dict):
                        items.append(o["aweme_info"])
                    if "aweme_list" in o and isinstance(o["aweme_list"], list):
                        for it in o["aweme_list"]:
                            if isinstance(it, dict):
                                if "aweme_info" in it and isinstance(it["aweme_info"], dict):
                                    items.append(it["aweme_info"])
                                else:
                                    items.append(it)
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)

            walk(data)

            for it in items:
                try:
                    vid = str(it.get("aweme_id") or it.get("group_id"))
                    if not vid:
                        continue
                    ct = it.get("create_time")
                    if ct is None and isinstance(it, dict):
                        ct = next((v for k, v in it.items() if k == "create_time"), None)
                    ct = int(ct) if ct is not None else 0
                    if ct < cutoff:
                        continue
                    vurl = f"https://www.douyin.com/video/{vid}"
                    collected[vurl] = ct
                    if len(collected) >= limit:
                        done.set()
                        return
                except Exception:
                    continue
        except Exception:
            pass


    page.on("response", on_response)

    try:
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(800)
    except Exception:
        pass

    start_ts = time.time()

    async def auto_scroll():
        try:
            while not done.is_set() and (time.time() - start_ts) < (timeout_ms / 1000):
                await page.mouse.wheel(0, 1200)
                await page.wait_for_timeout(2000)
        except Exception:
            pass

    scroll_task = asyncio.create_task(auto_scroll())

    try:
        await asyncio.wait_for(done.wait(), timeout=timeout_ms / 1000)
    except Exception:
        pass
    finally:
        try:
            scroll_task.cancel()
        except Exception:
            pass
        try:
            page.off("response", on_response)
        except Exception:
            pass

    urls_sorted = [u for u, _ in sorted(collected.items(), key=lambda x: x[1], reverse=True)]
    return urls_sorted[:limit]

async def collect_recent_waterfall_ids(page: Page, limit: int = 10) -> List[str]:
    """页面向下滚动加载后，获取前 10 个 `.search-result-card`，读取时间文本（如“8小时前”或“10月11日”），
    计算是否在最近 RECENT_DAYS 天内；若在，则取父容器 id（形如 `waterfall_item_...`）并返回列表（至多 limit 条）。"""
    cutoff_ts = int(time.time()) - RECENT_DAYS * 24 * 3600
    # 选取前 10 个 search-result-card 元素
    cards = await page.locator('.search-result-card').element_handles()
    cards = cards[:10]

    def parse_time_text(txt: str) -> int | None:
        # 支持 “N小时前”/“N分钟前” 与 “MM月DD日”，返回 Unix 秒级时间戳
        txt = (txt or '').strip()
        if not txt:
            return None
        m = re.match(r'^(\d+)\s*小时前$', txt)
        if m:
            hours = int(m.group(1))
            return int(time.time()) - hours * 3600
        m = re.match(r'^(\d+)\s*分钟前$', txt)
        if m:
            minutes = int(m.group(1))
            return int(time.time()) - minutes * 60
        m = re.match(r'^(\d+)\s*天前$', txt)
        if m:
            days = int(m.group(1))
            return int(time.time()) - days * 24 * 3600
        m = re.match(r'^(\d{1,2})月(\d{1,2})日$', txt)
        if m:
            month = int(m.group(1))
            day = int(m.group(2))
            now = datetime.now()
            dt = datetime(year=now.year, month=month, day=day, hour=0, minute=0, second=0)
            return int(dt.timestamp())
        return None

    results: List[str] = []
    for card in cards:
        try:
            # 时间文本位于示例中的 `.RY_wFBXl .dO8W7uoF`，内容形如 “ · 8小时前” 或 “ · 10月11日”
            time_el = await card.query_selector('.RY_wFBXl .dO8W7uoF')
            text = (await time_el.text_content()) if time_el else ''
            text = (text or '').strip().lstrip('· ')
            ts = parse_time_text(text)
            if ts is None or ts < cutoff_ts:
                continue
            # 获取父容器 id（形如 waterfall_item_...）
            parent = await card.evaluate_handle("el => el.closest('[id^=waterfall_item_]')")
            pid = await parent.get_property('id') if parent else None
            pid_val = (await pid.json_value()) if pid else None
            if isinstance(pid_val, str):
                m = re.match(r'^waterfall_item_(\d+)$', pid_val)
                if m:
                    results.append(m.group(1))
        except Exception:
            continue

    return results[:limit]

def load_uploaded_urls(path: str) -> set[str]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()

def append_uploaded_url(path: str, url: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(url + "\n")

def load_failed_urls(path: str) -> set[str]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return {line.split('\t', 1)[0].strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()

def append_failed_url(path: str, url: str, reason: str | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        if reason:
            f.write(f"{url}\t{reason}\n")
        else:
            f.write(url + "\n")

def upload_to_backend(video_url: str) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_BASE_URL}/feishu/upload_record",
            json={"page_url": video_url}, timeout=30,
            headers={"Content-Type": "application/json"}
        )
        data = resp.json()
        if not resp.ok:
            return {"ok": False, "status": resp.status_code, "data": data}
        return data
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def run(keyword: str):
    async with async_playwright() as p:
        browser = None
        try:
            browser, page = await open_bit_browser(p, BIT_BROWSER_ID)

            # 1) 跳转前开启监听并处理数据（只解析 search/single|search/item 的 JSON）
            collected_raw: List[tuple[str, int]] = []
            done = asyncio.Event()
            cutoff = int(time.time()) - RECENT_DAYS * 24 * 3600

            async def on_response(resp):
                try:
                    req = resp.request
                    rt = getattr(req, "resource_type", "") or ""
                    if rt not in ("xhr", "fetch"):
                        return
                    url = resp.url or ""
                    if ("search/single" not in url and "search/item" not in url):
                        return
                    ctype = resp.headers.get("content-type", "")
                    if "application/json" not in ctype and "json" not in ctype:
                        return
                    text = await resp.text()
                    data = json.loads(text)
                    items: list[dict] = []
                    def walk(o):
                        if isinstance(o, dict):
                            if "aweme_info" in o and isinstance(o["aweme_info"], dict):
                                items.append(o["aweme_info"])
                            if "aweme_list" in o and isinstance(o["aweme_list"], list):
                                for it in o["aweme_list"]:
                                    if isinstance(it, dict):
                                        if "aweme_info" in it and isinstance(it["aweme_info"], dict):
                                            items.append(it["aweme_info"])
                                        else:
                                            items.append(it)
                            for v in o.values():
                                walk(v)
                        elif isinstance(o, list):
                            for v in o:
                                walk(v)
                    walk(data)

                    for it in items:
                        try:
                            vid = str(it.get("aweme_id") or it.get("group_id"))
                            if not vid:
                                continue
                            ct = it.get("create_time")
                            if ct is None and isinstance(it, dict):
                                ct = next((v for k, v in it.items() if k == "create_time"), None)
                            ct = int(ct) if ct is not None else 0
                            vurl = f"https://www.douyin.com/video/{vid}"
                            collected_raw.append((vurl, ct))
                        except Exception:
                            continue
                except Exception:
                    pass

            page.on("response", on_response)

            # 2) 跳转到搜索页面
            await goto_douyin_search(page, keyword)

            time.sleep(2)
            
            # 3) 在监听期间同步向下滚动 20 次（每次固定等待 2 秒）
            try:
                for _ in range(20):
                    await page.mouse.wheel(0, 1200)
                    await page.wait_for_timeout(2000)
            except Exception:
                pass

            # 5) 再获取页面相关元素（最近 RECENT_DAYS 天内的前10卡片父ID）
            ids_first = await collect_recent_waterfall_ids(page, limit=10)
            print(f"最近 {RECENT_DAYS} 天内的前10卡片父ID(初次): {ids_first}")

            # 6) 将鼠标移动到“筛选”上并点击“最新发布”，监听保持开启以捕获新数据
            try:
                filt = page.locator('span.P1BREWal')
                await filt.first.hover(timeout=2000)
            except Exception:
                try:
                    await page.get_by_text('筛选', exact=False).first.hover(timeout=2000)
                except Exception:
                    pass
            # 点击“最新发布”
            try:
                await page.get_by_text('最新发布', exact=False).first.click(timeout=3000)
            except Exception:
                try:
                    await page.locator('span.eXMmo3JR', has_text='最新发布').first.click(timeout=3000)
                except Exception:
                    pass
            # 点击后同步滚动一小段以触发新结果加载（仍固定2秒间隔）
            try:
                for _ in range(20):
                    await page.mouse.wheel(0, 1200)
                    await page.wait_for_timeout(2000)
            except Exception:
                pass
            

            ids_second = await collect_recent_waterfall_ids(page, limit=10)
            print(f"最近 {RECENT_DAYS} 天内的前10卡片父ID(二次): {ids_second}")

            # 合并两次 ID，去重保持顺序
            all_ids: List[str] = []
            seen = set()
            for _id in list(ids_first) + list(ids_second):
                if _id not in seen:
                    seen.add(_id)
                    all_ids.append(_id)

            # 4) 统一处理收集的原始数据：去重、按时间过滤
            collected: Dict[str, int] = {}
            for vurl, ct in collected_raw:
                if ct >= cutoff:
                    collected[vurl] = max(ct, collected.get(vurl, 0))
            urls_unsorted = list(collected.keys())

            # 将合并后的 all_ids 拼接成完整视频链接，追加到 urls 中
            for _id in all_ids:
                urls_unsorted.append(f"https://www.douyin.com/video/{_id}")

            print(f"监听收集到 {len(urls_unsorted)} 个视频链接（含拼接自ID）")

            # 加载已上传集合和失败集合，并过滤重复/失败链接
            uploaded_seen = load_uploaded_urls(UPLOADED_URLS_FILE)
            failed_seen = load_failed_urls(FAILED_URLS_FILE)
            urls_to_upload = [u for u in urls_unsorted if u not in uploaded_seen and u not in failed_seen]
            if uploaded_seen or failed_seen:
                print(f"已存在 {len(uploaded_seen)} 条历史成功记录、{len(failed_seen)} 条失败记录，本次待上传 {len(urls_to_upload)} 条")

            # 按 2 秒频率上传，并在成功后立刻将链接写入 uploaded_urls.txt
            # 同时收集失败的链接（含服务器端错误）
            results = []
            failed = []
            for idx, url in enumerate(urls_to_upload, start=1):
                try:
                    resp = upload_to_backend(url)
                    record = {"url": url, **resp}
                    results.append(record)
                    if not resp.get("ok", True):
                        failed.append({
                            "url": url,
                            "status": resp.get("status"),
                            "error": resp.get("error"),
                            "data": resp.get("data"),
                        })
                        reason = resp.get("error") or json.dumps(resp.get("data"), ensure_ascii=False)
                        append_failed_url(os.path.join(os.path.dirname(UPLOADED_URLS_FILE), "failed_urls.txt"), url, reason=reason)
                        print(f"[{idx}/{len(urls_to_upload)}] 上传失败 {url}: {resp}")
                    else:
                        append_uploaded_url(UPLOADED_URLS_FILE, url)
                        uploaded_seen.add(url)
                        print(f"[{idx}/{len(urls_to_upload)}] 上传成功 {url}")
                except Exception as e:
                    failed.append({"url": url, "exception": str(e)})
                    results.append({"url": url, "ok": False, "error": str(e)})
                    append_failed_url(os.path.join(os.path.dirname(UPLOADED_URLS_FILE), "failed_urls.txt"), url, reason=str(e))
                    print(f"[{idx}/{len(urls_to_upload)}] 上传异常 {url}: {e}")
                await page.wait_for_timeout(2000)

            return {"urls": urls_unsorted, "ids": all_ids, "upload": {"results": results, "failed": failed}}
        finally:
            print("----")

def load_keywords(path: str) -> List[str]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except FileNotFoundError:
        return []

if __name__ == "__main__":
    kws = load_keywords(KEYWORDS_FILE)
    print("开始关键词采集:", kws)

    async def run_all(keywords: List[str]):
        results = []
        for kw in keywords:
            print("开始关键词采集:", kw)
            out = await run(kw)
            results.append({"keyword": kw, **(out or {})})
            await asyncio.sleep(1)
        return results

    out = asyncio.run(run_all(kws))
    print(json.dumps(out, ensure_ascii=False, indent=2))
