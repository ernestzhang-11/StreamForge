from datetime import datetime
import json
import logging
import os
import re
import sys
import traceback
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse, urlunparse

current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

possible_xhs_paths = [
    os.path.join(project_root, "xhs_downloader"),
    os.path.join(project_root, "server", "xhs_downloader"),
    os.path.join(current_dir, "xhs_downloader"),
]
for xhs_path in possible_xhs_paths:
    if os.path.isdir(xhs_path) and xhs_path not in sys.path:
        sys.path.insert(0, xhs_path)

from product_mapping_service import load_product_mapping, map_product_name, extract_product_info

from dotenv import load_dotenv
from f2.apps.douyin.crawler import DouyinCrawler, PostDetail
from f2.apps.douyin.db import AsyncUserDB
from f2.apps.douyin.dl import DouyinDownloader
from f2.apps.douyin.handler import DouyinHandler
from f2.apps.douyin.utils import AwemeIdFetcher
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

import feishu_table as feishu
from xhs_downloader.source import Settings, XHS


load_dotenv()

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", os.path.join(os.path.dirname(__file__), "downloads"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")



def upload_video_to_feishu(aweme_data: Dict[str, Any], page_url: str) -> Dict[str, Any]:
    video_path = aweme_data["video_path"]
    ct_raw = aweme_data.get("create_time")
    try:
        ct_sec = int(ct_raw)
        ct_str = datetime.fromtimestamp(ct_sec).strftime("%Y年%m月%d日%H_%M_%S")
    except Exception:
        try:
            dt = datetime.fromisoformat(str(ct_raw).replace("Z", "+00:00"))
        except Exception:
            dt = None
        ct_str = dt.strftime("%Y年%m月%d日%H_%M_%S") if dt else str(ct_raw)

    filename = f"{ct_str}_{aweme_data['author']['nickname']}_{aweme_data['aweme_id']}.mp4"
    upload_result = feishu.upload_file_to_bitable(
        file_path=video_path,
        file_name=filename,
        parent_node=feishu.APP_TOKEN,
        parent_type="bitable_file",
    )
    if not upload_result.get("success"):
        return upload_result

    file_token = upload_result.get("file_token")
    if not file_token:
        return {"success": False, "message": "上传成功但未获取到 file_token"}

    access_token = upload_result.get("access_token") or feishu.get_tenant_access_token()

    product_mapping = load_product_mapping()
    product_name = extract_product_info(aweme_data)
    mapped_product_name = map_product_name(product_name, product_mapping)

    title = aweme_data.get("desc") or ""

    record_fields = {
        feishu.FIELD_REMARK: '速发',
        feishu.FIELD_TITLE: title,
        feishu.FIELD_PRODUCT_NAME: mapped_product_name,
        feishu.FIELD_VIDEO_ID: aweme_data.get("aweme_id") or "",
        feishu.FIELD_ATTACHMENT: [
            {
                "file_token": file_token,
                "name": filename,
                "type": "file",
            }
        ],
    }

    if mapped_product_name and mapped_product_name != product_name:
        record_fields["品"] = mapped_product_name

    record_success = feishu.create_douyin_record(record_fields, access_token=access_token)
    if not record_success:
        return {"success": False, "message": "飞书表格记录创建失败"}

    return {
        "success": True,
        "file_token": file_token,
        "message": "飞书表格记录创建成功",
        "aweme_id": aweme_data["aweme_id"],
    }
def extract_video_id_from_url(page_url: str) -> str | None:
    """支持两种格式：
    1) https://www.douyin.com/video/{id}
    2) https://www.douyin.com/user/...?...&modal_id={id}
    返回提取到的 video_id 或 None。
    """
    try:
        if not page_url:
            return None
        # 优先匹配 /video/{id}
        m = re.search(r"/video/(\d+)", page_url)
        if m:
            return m.group(1)
        # 再从查询参数 modal_id 抓取
        parsed = urlparse(page_url)
        qs = parse_qs(parsed.query or "")
        modal_id = qs.get("modal_id")
        if modal_id and len(modal_id) > 0 and modal_id[0].isdigit():
            return modal_id[0]
        return None
    except Exception:
        return None

async  def download_with_f2(video_id: str):
    kwargs = {
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Referer": "https://www.douyin.com/",
        },
        "proxies": {"http://": None, "https://": None},
        "cookie": "bd_ticket_guard_client_web_domain=2; live_use_vvc=%22false%22; store-region=cn-hb; store-region-src=uid; hevc_supported=true; SelfTabRedDotControl=%5B%5D; xgplayer_user_id=73509612205; xgplayer_device_id=97526515781; n_mh=9-mIeuD4wZnlYrrOvfzG3MuT6aQmCUtmr8FxV8Kl8xY; __live_version__=%221.1.3.519%22; SearchMultiColumnLandingAbVer=1; SEARCH_RESULT_LIST_TYPE=%22multi%22; theme=%22light%22; enter_pc_once=1; is_staff_user=false; d_ticket=37143149636914e9578d19de548f6905cfb72; passport_assist_user=Cj8Ts8FVwRqJr1v98EWtLj_Gy9RxQdvd1QBRP_ljzu_gvNNnalyA8fR3UDv2RDRmZn3EUOdysavh9ERIDpMUChEaSgo8AAAAAAAAAAAAAE891LiUK62M1U20pNLuK_iec-5n14zYMF6qyhMBeH5-pmBooHTxvvZIiPxkQ0kYdT9CEN7y9g0Yia_WVCABIgEDEPxTnQ%3D%3D; uid_tt=6feaf6442a589053a8fd82c49b31d519; uid_tt_ss=6feaf6442a589053a8fd82c49b31d519; sid_tt=8d310cc387442877d3aa4076790d75d4; sessionid_ss=8d310cc387442877d3aa4076790d75d4; login_time=1752669402602; __druidClientInfo=JTdCJTIyY2xpZW50V2lkdGglMjIlM0EyOTglMkMlMjJjbGllbnRIZWlnaHQlMjIlM0E0NDclMkMlMjJ3aWR0aCUyMiUzQTI5OCUyQyUyMmhlaWdodCUyMiUzQTQ0NyUyQyUyMmRldmljZVBpeGVsUmF0aW8lMjIlM0EyLjM5MjUwMDE2MjEyNDYzNCUyQyUyMnVzZXJBZ2VudCUyMiUzQSUyMk1vemlsbGElMkY1LjAlMjAoV2luZG93cyUyME5UJTIwMTAuMCUzQiUyMFdpbjY0JTNCJTIweDY0KSUyMEFwcGxlV2ViS2l0JTJGNTM3LjM2JTIwKEtIVE1MJTJDJTIwbGlrZSUyMEdlY2tvKSUyMENocm9tZSUyRjEzNi4wLjAuMCUyMFNhZmFyaSUyRjUzNy4zNiUyMiU3RA==; UIFID_TEMP=28ea90c1b0cf804752225259882c701fb12323f08ef828fc1032b615e29efbbe284c71b6b91371623513ffcf74f19a3685d9b5481ee218c0226c15853a3987f771501a4cd016d2934472916e0fe218aa; fpk1=U2FsdGVkX1/Nox6hMzmakvRdvL55xEuVxx0/Qgy2zFFtXA3ogvorvBlxwwK2eahHRoI8eYBFqj0rx3y2SWAYDw==; fpk2=0e0369e2813db7deb26e5937c353aab4; UIFID=28ea90c1b0cf804752225259882c701fb12323f08ef828fc1032b615e29efbbe35cc4916a88c9a1d2c4f38e526102eecaba3629149dc23be141a59b83c16f86f2e9e5c5c1923c027773de62a4dee2b618f6cf724c95615849c9dc3636d2f2ef1a13956440290f0ca734787dbd691848f5ac1c981de663d8f0cd05af54b924e53b07a44b6e05a5d7aaa565ae8875085625b75a1c5cb83670d36e1b43d7271b5b0; __security_mc_1_s_sdk_crypt_sdk=9c09da64-4128-a242; __security_mc_1_s_sdk_cert_key=a882b0fc-4b8d-8390; passport_csrf_token=92674daafb36b50004014d008e155001; passport_csrf_token_default=92674daafb36b50004014d008e155001; s_v_web_id=verify_mfweipo0_kNeXCV5e_PNz1_4KhU_B6fn_KVYujburyP1Z; __security_mc_1_s_sdk_sign_data_key_web_protect=531caaa7-460e-baf7; is_dash_user=1; sid_guard=8d310cc387442877d3aa4076790d75d4%7C1760694863%7C5184000%7CTue%2C+16-Dec-2025+09%3A54%3A23+GMT; sessionid=8d310cc387442877d3aa4076790d75d4; sid_ucp_v1=1.0.0-KGFmMjJjNGEwOGUzMzEzNmFjNzAyZDViYWQzOGQ4MTA3YTRjNWU0NGUKIAjj1JCqhM0GEM-kyMcGGO8xIAwwwKmRrAY4B0D0B0gEGgJobCIgOGQzMTBjYzM4NzQ0Mjg3N2QzYWE0MDc2NzkwZDc1ZDQ; ssid_ucp_v1=1.0.0-KGFmMjJjNGEwOGUzMzEzNmFjNzAyZDViYWQzOGQ4MTA3YTRjNWU0NGUKIAjj1JCqhM0GEM-kyMcGGO8xIAwwwKmRrAY4B0D0B0gEGgJobCIgOGQzMTBjYzM4NzQ0Mjg3N2QzYWE0MDc2NzkwZDc1ZDQ; publish_badge_show_info=%220%2C0%2C0%2C1760946606136%22; download_guide=%223%2F20251020%2F0%22; session_tlb_tag=sttt%7C13%7CjTEMw4dEKHfTqkB2eQ111P_________AFMFsDkfR2RWWZu4UOI714T_KV-nrHbwCQ5EoI_22oZE%3D; playRecommendGuideTagCount=13; totalRecommendGuideTagCount=13; dy_swidth=1325; dy_sheight=745; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1325%2C%5C%22screen_height%5C%22%3A745%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A24%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.976%7D; WallpaperGuide=%7B%22showTime%22%3A1760947412272%2C%22closeTime%22%3A0%2C%22showCount%22%3A3%2C%22cursor1%22%3A86%2C%22cursor2%22%3A28%7D; __ac_nonce=068f90467006fa53e1dde; __ac_signature=_02B4Z6wo00f01Ef3sJAAAIDAybrGpBc2NsxH17QAAHkMa1; strategyABtestKey=%221761150057.502%22; ttwid=1%7CeG1xfsoe_CWPEpcGmmRqV6VGOr2TwQnfHP5012UIHGg%7C1761150056%7C89a27cc0424490a1a4d906dc673af79c17b655cf2506d07c9c2190a9a94317d5; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e5927666d776a686028607d71606b766c6a6b3f2a2a646063606d616d61666c6c606a66646e636a677564646a696d6c756e667562662a666a6b71606b715a7666776c7571762a666a757c2b6f765927295927666d776a686028607d71606b766c6a6b3f2a2a61676f67606875696f6d66686d69637563646664696a686a6b6f756469756e6a2a7666776c7571762a6c6b76756066716a772b6f76592758272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f273d363436333535303434333234272927676c715a75776a716a666a69273f2763646976602778; bit_env=KyGujVy1BHnPGXHbUj1rhYqAvMzTMs0IlZUWX8883LhiJm4VEripCHKWh8PXo1Rg69ofjFdXXX5ZZdHKPIauf8DT3CiP31pUQ-4DuzsawZQ6pPC_xnA4VPyqgLSyn8AECnOi3jfyf8pbVkMeGxmGAMNY2okCUNyoRlvQh2u1VnfG42GdLVSm4yLnm2BFLaxn5Z-IPQgd8AVdmjQ0hkVRNnncsXgOeYNAmwNYzSi_6lUba5PQrqGiityhxxRtziKuXJLqKwDTejbYLJ0kTLkL966FXvc5ylyyh5ZNt86BpxHqDbaytTdOUEQ0e17e3ub7h43LBBRHGUZHOZClrJ-m6z-TcVm728bmkD52fK1IzCd2ktLppOvgFdH_73nomfkFTN153ajby92eME5NubQjp-dUzUkZjs-29IFBjTobCBV0Z480Pll_JJJ8VinErc8WJSkpTmYazUMiu8c9TNe86cgoUF8QfvDJvyK-lFIIVHFKl1qMPGSA16M0qnYy1tzp; gulu_source_res=eyJwX2luIjoiYmM5OWY5NGU3MmYzZDQ4ZDRiMWU2Mzc1MzQ3MzY4YTYwNzI5OTJmZWE2ZDJhMDFiZDE3ZWVmZjAzMTk3ZDk3NyJ9; passport_auth_mix_state=cvovi23y6uge1gxyl18oxsz13c0m2dcp; odin_tt=b9efcd00b3cf615069a082bcd3307278e4be61d61e089b9f811acaa975b54481fd23937ec9628b1740e60460a2cee11a8f857dee614a3c03a45dca2b8c210162; biz_trace_id=af6fa95c; IsDouyinActive=true; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAAk33rRYtXKgtE1sOVuGF19VouIP6KwRZw49L6iJntY7E%2F1761235200000%2F0%2F0%2F1761150881480%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAk33rRYtXKgtE1sOVuGF19VouIP6KwRZw49L6iJntY7E%2F1761235200000%2F0%2F1761150281480%2F0%22; home_can_add_dy_2_desktop=%221%22; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCQytIbWhFbklkQitDU1dmQlVoQTNKRnVlOHFNcFJ4Q1ZlV1MrZEVyQ2xZNVFGdC9odnZqa0RUM1B5MEQwMGswOGpuaUR1UnJFaVp4eklnMkF6WXdFckE9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJDK0htaEVuSWRCK0NTV2ZCVWhBM0pGdWU4cU1wUnhDVmVXUytkRXJDbFk1UUZ0L2h2dmprRFQzUHkwRDAwazA4am5pRHVSckVpWnh6SWcyQXpZd0VyQT0iLCJ0c19zaWduIjoidHMuMi4wOGJkMDhiNGEzMTllMWI2YjkxMGEyOWUyMWZmYzc0NWRjMjkyN2ZmN2I0MDg2YWI5ZWZiZGNmMzdhMGU5Zjg4YzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsInJlcV9jb250ZW50Ijoic2VjX3RzIiwicmVxX3NpZ24iOiJvdTVHSjRJa3N3dTE5TW45TDNTcjlwQWRSdW8vdStkdnBHeWh2VVhrbWs4PSIsInNlY190cyI6IiNSM0lUQzMxWUF6NVBnYnhqeVJFdXA5SmYyRC91UURaZHRUMWFpVzlQM01OMlgyeVZsb0xrRjhsMERuQjIifQ%3D%3D",
        "url": f"https://www.douyin.com/{video_id}",
        'video': True,  # 下载视频
        'music': False,  # 不下载音乐
        'cover': False,  # 不下载封面
        'desc': False,  # 不下载文案
        'folderize': False,  # 不创建子文件夹
        'interval': 'all',  # 下载所有
        'path': DOWNLOAD_DIR,
        'naming':"{aweme_id}_{create}"
    }

    async with DouyinCrawler(kwargs) as crawler:
        params = PostDetail(aweme_id=video_id)
        post_detail = await crawler.fetch_post_detail(params)
    aweme_data = post_detail['aweme_detail']
    

    # aweme_data = await DouyinHandler(kwargs).fetch_one_video(aweme_id=video_id)
    user_path = DOWNLOAD_DIR
    downloader = DouyinDownloader(kwargs)

    aweme_datas = []
    dl_aweme_data = {
                    'aweme_id': aweme_data['aweme_id'],
                    'desc': aweme_data['desc'],
                    'create_time': aweme_data['create_time'],
                    'sec_user_id': aweme_data['author']['sec_uid'],
                    'video_play_addr': aweme_data['video']['play_addr']['url_list'][0],
                    'is_prohibited': False,
                    'private_status': 0,
                    'aweme_type': 0,  # 视频类型,
                    'nickname': aweme_data['author']['nickname']
    }
    aweme_datas.append(dl_aweme_data)
    await downloader.create_download_tasks(kwargs=kwargs, aweme_datas=aweme_datas, user_path=user_path)

    video_path = os.path.join(user_path, f"{aweme_data['aweme_id']}_{aweme_data['create_time']}_video.mp4")
    if not video_path or not os.path.isfile(video_path):
        logging.error("视频未找到或未成功下载: %s", video_path)
        raise FileNotFoundError(f"视频未找到: {video_path}")
        
    aweme_data["video_path"] = video_path

    return aweme_data


@app.route("/feishu/upload_record", methods=["POST"])
def upload_record():
    #  检查链接
    j = request.get_json(force=True, silent=True) or {}
    page_url = j.get("page_url")
    if not page_url or not isinstance(page_url, str):
        return jsonify({"ok": False, "error": "缺少或非法的 page_url"}), 400
    parsed = urlparse(page_url)
    if parsed.scheme not in ("http", "https") or parsed.netloc not in ("www.douyin.com", "douyin.com"):
        return jsonify({"ok": False, "error": "链接不合法，只支持抖音页面URL"}), 400
    video_id = extract_video_id_from_url(page_url)
    if not video_id:
        return jsonify({"ok": False, "error": "无法从链接提取 video_id"}), 400

    try:
        # 下载前：先在飞书多维表中按 video_id 检索是否已存在
        existing = feishu.search_record_by_video_id(video_id, page_size=1)
        # 以 total 是否大于 0 来判断是否存在
        if isinstance(existing, dict) and existing.get("total", 0) > 0:
            return jsonify({
                "ok": True,
                "message": "该视频已上传过（根据 video_id 命中）",
                "exists": True,
                "records": existing.get("items", []),
                "total": existing.get("total", 0)
            }), 200

        # 下载视频
        import asyncio
        aweme_data = asyncio.run(download_with_f2(video_id))

        # 上传视频到飞书
        upload_result = upload_video_to_feishu(aweme_data, page_url)
        if isinstance(upload_result, dict) and upload_result.get("success"):
            return jsonify({"ok": True, "message": upload_result.get("message", "视频上传成功"), "result": upload_result}), 200
        else:
            # 失败时也返回详细信息，便于前端展示与排查
            return jsonify({"ok": False, "message": (upload_result or {}).get("message", "视频上传失败"), "result": upload_result}), 500
    except Exception as e:
        logging.error("upload_record failed: %s", e)
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {str(e)}"}), 500

@app.route("/xhs/parse_note", methods=["GET", "POST"])
def parse_xhs_note():
    try:
        query_params: Dict[str, str] = {}
        if request.method == "GET":
            payload = request.args.to_dict(flat=True)
            query_params.update(payload)
        else:
            payload = request.get_json(force=True, silent=True) or {}
            if isinstance(payload, dict):
                query_params.update({str(k): str(v) for k, v in payload.items() if v is not None})

        for key, value in request.args.items():
            if value is not None and str(value).strip():
                query_params[str(key)] = str(value)

        base_url = query_params.get("url", "").strip()
        if not base_url:
            return jsonify({"ok": False, "error": "缺少必需参数 url"}), 400

        parsed_url = urlparse(base_url)
        base_query = parse_qs(parsed_url.query, keep_blank_values=True)
        merged_query = {}
        for key, values in base_query.items():
            if values:
                merged_query[key] = values[-1]
        for key, value in query_params.items():
            if key == "url":
                continue
            value_str = str(value).strip()
            if value_str:
                merged_query[key] = value_str

        final_query_string = "&".join(
            f"{key}={value}" for key, value in merged_query.items()
        )
        url = urlunparse(parsed_url._replace(query=final_query_string))


        # 实例对象
        work_path = DOWNLOAD_DIR  # 作品数据/文件保存根路径，默认值：项目根路径
        folder_name = "xhs"  # 作品文件储存文件夹名称（自动创建），默认值：Download
        name_format = "作品标题 发布时间 作品ID"
        user_agent = ""  # User-Agent
        cookie = "gid=yYd2DyDqyWi2yYd2DyDJi4fDJYDluSUTYMUqhy9l7ShU6T28S4Wuvx888qWYKqY88yi0WiDq; a1=197ce1290423idqzjsg7hsrcugu3a13wd08m7yb0q50000412668; webId=f3a1a25308658bd5b4aae8b43c32c877; customerClientId=450717816262315; x-user-id-chengfeng.xiaohongshu.com=67f0badd000000000e01e3aa; abRequestId=f3a1a25308658bd5b4aae8b43c32c877; x-user-id-pgy.xiaohongshu.com=67f0badd000000000e01e3aa; x-user-id-creator.xiaohongshu.com=637f22ae000000001f016b78; x-user-id-fuwu.xiaohongshu.com=67f0badd000000000e01e3aa; x-user-id-school.xiaohongshu.com=67f0badd000000000e01e3aa; x-user-id-ark.xiaohongshu.com=67f0badd000000000e01e3aa; access-token-creator.xiaohongshu.com=customer.creator.AT-68c517556579582598742016duodpo7ujjtu3ga1; galaxy_creator_session_id=SpNvn7CTc5ppXqUjyT0C4apfx8tqu0Cz6bf8; galaxy.creator.beaker.session.id=1759403288114097431182; access-token-chengfeng.xiaohongshu.com=customer.ad_wind.AT-68c517560580430535557126jxszodjyjbezmsmj; access-token-ark.xiaohongshu.com=customer.ark.AT-68c517562392902439419904z7kwckuxb7t1mdgk; customer-sso-sid=68c517564424610949038084zkoc9ymcqn1o1nzg; access-token-fuwu.xiaohongshu.com=customer.fuwu.AT-68c517564424615243825152ee68hq01966biurf; access-token-fuwu.beta.xiaohongshu.com=customer.fuwu.AT-68c517564424615243825152ee68hq01966biurf; webBuild=4.83.1; beaker.session.id=40893282ec867fc3f781b15aa7c099d30aef47d7gAJ9cQEoVQhfZXhwaXJlc3ECY2RhdGV0aW1lCmRhdGV0aW1lCnEDVQoH6QobBR4MCaBThVJxBFUDX2lkcQVVIDlhMmI4Y2Q2ZDdiNTQ1ODJiZjUyMjY5YTJhODEwYTJjcQZVDl9hY2Nlc3NlZF90aW1lcQdHQdo/dy4T+M9VDl9jcmVhdGlvbl90aW1lcQhHQdo/bHiyn5B1Lg==; xsecappid=xhs-pc-web; web_session=040069b20b61e62f3b2eacb6c83a4bd3a0b3ff; unread={%22ub%22:%2268ee1d03000000000703719a%22%2C%22ue%22:%2268f62000000000000302db12%22%2C%22uc%22:21}; websectiga=3fff3a6f9f07284b62c0f2ebf91a3b10193175c06e4f71492b60e056edcdebb2; sec_poison_id=6b4edcc8-9a2c-42fa-800c-1af30f5ce6b7; loadts=1761476993393"  # 小红书网页版 Cookie，无需登录，可选参数，登录状态对数据采集有影响
        timeout = 10  # 请求数据超时限制，单位：秒，默认值：10
        chunk = 1024 * 1024 * 10  # 下载文件时，每次从服务器获取的数据块大小，单位：字节
        max_retry = 2  # 请求数据失败时，重试的最大次数，单位：秒，默认值：5
        image_format = "PNG"  # 图文作品文件下载格式，支持：AUTO、PNG、WEBP、JPEG、HEIC
        image_download = True  # 图文、图集作品文件下载开关
        video_download = True  # 视频作品文件下载开关
        live_download = True  # 图文动图文件下载开关
        download_record = False  # 是否记录下载成功的作品 ID
        language = "zh_CN"  # 设置程序提示语言
        read_cookie = None  # 读取浏览器 Cookie，支持设置浏览器名称（字符串）或者浏览器序号（整数），设置为 None 代表不读取

        async def _do_parse() -> dict:
            async with XHS(
                work_path=work_path,
                folder_name=folder_name,
                name_format=name_format,
                user_agent=user_agent,
                cookie=cookie,
                timeout=timeout,
                chunk=chunk,
                max_retry=max_retry,
                image_format=image_format,
                image_download=image_download,
                video_download=video_download,
                live_download=live_download,
                download_record=download_record,
                language=language,
                read_cookie=read_cookie,
            ) as xhs:
                data = await xhs.extract(url, True, cookie=cookie)
                print(data)
                
                return {"ok": True, "data": data}

        import asyncio

        result = asyncio.run(_do_parse())
        # 上传到飞书多维表格中
        try:
            if result.get("ok") and isinstance(result.get("data"), list):
                access_token = feishu.get_tenant_access_token()
                # 逐条上传（当前示例只处理第一条）
                item = result["data"][0]
                title = item.get("作品标题") or item.get("作品描述")
                text = item.get("作品描述")
                note_link = item.get("作品链接")
                like_count = item.get("点赞数量")
                author = item.get("作者昵称")
                publish_time_raw = item.get("发布时间")
                last_edit_time_raw = item.get("最后更新时间")
                note_id = item.get("作品ID")
                comment_count = item.get("评论数量")
                collect_count = item.get("收藏数量")

                # 优先使用本地已下载文件
                base_dir = item.get("文件保存路径") or DOWNLOAD_DIR
                filename = item.get("filename") or title or (note_id or "xhs")
                # 规范化时间字符串并转为 Unix 时间戳（秒）
                def normalize_dt(s: str) -> str:
                    if not s:
                        return ""
                    s = s.replace("_", " ")
                    parts = s.split()
                    if len(parts) >= 2:
                        parts[1] = parts[1].replace(".", ":")
                        return parts[0] + " " + parts[1]
                    return s.replace(".", ":")

                def parse_timestamp(raw: str) -> int | None:
                    raw = normalize_dt(raw)
                    if not raw:
                        return None
                    try:
                        dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
                        return int(dt.timestamp() * 1000)
                    except ValueError:
                        try:
                            return int(float(raw))
                        except (TypeError, ValueError):
                            return None

                publish_time_ts = parse_timestamp(publish_time_raw)
                last_edit_time_ts = parse_timestamp(last_edit_time_raw)

                def upload_local_asset(asset_path: str, asset_name: str) -> str | None:
                    if not os.path.isfile(asset_path):
                        return None
                    upload_result = feishu.upload_file_to_bitable(
                        file_path=asset_path,
                        file_name=asset_name,
                        parent_node=feishu.XHS_APP_TOKEN,
                        parent_type="bitable_file",
                        access_token=access_token,
                    )
                    if not upload_result.get("success"):
                        logging.warning("上传资源失败: %s", upload_result.get("message"))
                        return None
                    file_token_value = upload_result.get("file_token")
                    if not file_token_value:
                        logging.warning("上传成功但没有返回 file_token")
                        return None
                    return file_token_value

                # 上传封面（仅使用本地已下载文件）
                cover_token = None
                try:
                    possible_cover_extensions = [
                        (item.get('image_format') or 'png').lower(),
                        'png',
                        'jpg',
                        'jpeg',
                        'webp',
                    ]
                    for ext in possible_cover_extensions:
                        cover_path_candidate = os.path.join(base_dir, f"{filename}_1.{ext}")
                        cover_token = upload_local_asset(cover_path_candidate, os.path.basename(cover_path_candidate))
                        if cover_token:
                            break
                except Exception:
                    cover_token = None

                # 上传图片
                img_tokens = []
                if item['作品类型'] == '图文':
                    for i, img_download_path in enumerate(item['下载地址']):
                        img_name = f"{filename}_{i+1}.png"
                        img_path_candidate = os.path.join(base_dir, img_name)
                        img_token = upload_local_asset(img_path_candidate, os.path.basename(img_path_candidate))
                        if img_token:
                            img_tokens.append(img_token)


                # 上传视频（仅使用本地已下载文件）
                video_token = None
                try:
                    possible_video_extensions = ["mp4", "mov"]
                    for ext in possible_video_extensions:
                        video_path_candidate = os.path.join(base_dir, f"{filename}.{ext}")
                        video_token = upload_local_asset(video_path_candidate, os.path.basename(video_path_candidate))
                        if video_token:
                            break
                except Exception:
                    video_token = None

                # 组装字段
                fields = {}
                if title: fields['标题'] = title
                if note_link: fields['笔记链接'] = note_link
                if like_count is not None: fields['点赞数'] = str(like_count)
                if author: fields['作者'] = author
                if publish_time_ts is not None:
                    fields['发布时间'] = publish_time_ts
                if last_edit_time_ts is not None:
                    fields['最后编辑时间'] = last_edit_time_ts
                if note_id: fields['笔记ID'] = note_id
                if comment_count is not None: fields['评论数'] = str(comment_count)
                if collect_count is not None: fields['收藏数'] = str(collect_count)
                if text: fields['文案'] = text

                if cover_token:
                    fields['封面'] = [{
                        'file_token': cover_token,
                        'name': f"{filename}_cover",
                        'type': 'file',
                    }]

                if video_token:
                    fields['视频'] = [{
                        'file_token': video_token,
                        'name': f"{filename}.mp4",
                        'type': 'file',
                    }]

                if len(img_tokens) > 0:
                    img_filds=[]
                    for i, img_token in enumerate(img_tokens):
                        img_filds.append({
                            'file_token': img_token,
                            'name': f"{filename}_{i}.png",
                            'type': 'file',
                        })

                    fields['图片'] = img_filds

                ok = feishu.create_xhs_record(fields, access_token=access_token)
                result["feishu"] = {"ok": ok, "fields": fields}
        except Exception as e:
            result["feishu_error"] = str(e)
        
        return jsonify(result), 200
    except Exception as e:
        logging.error("parse_xhs_note failed: %s", e)
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)