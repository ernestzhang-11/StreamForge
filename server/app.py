from datetime import datetime
import json
import logging
import os
import re
import sys
import traceback
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

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
from xhs_provider import get_xhs_apis_class
from xhs_url_parser import normalize_xhs_url, extract_note_info_from_url
from xhs_downloader_util import download_note as download_xhs_note
from xhs_handlers import parse_note_api_mode, parse_note_web_mode, upload_note_to_feishu


load_dotenv()

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", os.path.join(os.path.dirname(__file__), "downloads"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

XHS_COOKIE = os.getenv("XHS_COOKIE", "gid=yYd2DyDqyWi2yYd2DyDJi4fDJYDluSUTYMUqhy9l7ShU6T28S4Wuvx888qWYKqY88yi0WiDq; a1=197ce1290423idqzjsg7hsrcugu3a13wd08m7yb0q50000412668; webId=f3a1a25308658bd5b4aae8b43c32c877; customerClientId=450717816262315; x-user-id-chengfeng.xiaohongshu.com=67f0badd000000000e01e3aa; abRequestId=f3a1a25308658bd5b4aae8b43c32c877; x-user-id-pgy.xiaohongshu.com=67f0badd000000000e01e3aa; x-user-id-creator.xiaohongshu.com=637f22ae000000001f016b78; x-user-id-fuwu.xiaohongshu.com=67f0badd000000000e01e3aa; x-user-id-school.xiaohongshu.com=67f0badd000000000e01e3aa; x-user-id-ark.xiaohongshu.com=67f0badd000000000e01e3aa; access-token-ark.xiaohongshu.com=customer.ark.AT-68c517562392902439419904z7kwckuxb7t1mdgk; customer-sso-sid=68c517570751913819783169q4h64286mumotqdn; access-token-chengfeng.xiaohongshu.com=customer.ad_wind.AT-68c517570751913819799553r1o9fqeirdrgflh2; solar.beaker.session.id=AT-68c517571272176093167616dsdsuftdnydvncj6; access-token-pgy.xiaohongshu.com=customer.pgy.AT-68c517571272176093167616dsdsuftdnydvncj6; access-token-pgy.beta.xiaohongshu.com=customer.pgy.AT-68c517571272176093167616dsdsuftdnydvncj6; web_session=040069b20b61e62f3b2e7ab3233b4b6b387f9e; webBuild=4.85.1; xsecappid=xhs-pc-web; websectiga=9730ffafd96f2d09dc024760e253af6ab1feb0002827740b95a255ddf6847fc8; sec_poison_id=787efd0f-bccc-4684-b5f3-0229ede63d75; acw_tc=0a0bb06417631201434704128e73dd25e46b426462e25c369ded6cc9398049; loadts=1763120264511; unread={%22ub%22:%22691129950000000003013bc9%22%2C%22ue%22:%226915fa47000000001b0334e3%22%2C%22uc%22:11}")
XHS_MODE = os.getenv("XHS_MODE", "api").lower()
# XHS_MODE = os.getenv("XHS_MODE", "web").lower()

def upload_video_to_feishu(aweme_data: Dict[str, Any], channel: str = "") -> Dict[str, Any]:
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

    if channel and channel == "bit_playwright":
        if not product_name:
            return {"success": False, "message": "飞书表格记录创建失败，产品名称IS NONE"}

        find = False       
        for keyword, mapped_value in product_mapping.items():
            if keyword in product_name:
                find = True
                break

        if not find:     
            print(f"product_name: {product_name}")
            return {"success": False, "message": "飞书表格记录创建失败，未找到对应的产品名称 "+ product_name}

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
        'naming':"{aweme_id}_{create}",
        'timeout': 30,  # 设置超时时间
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
    channel = j.get("channel")
    if channel:
        logging.info("upload_record channel=%s", channel)

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
        
        # 修复事件循环冲突问题 - 使用现有的事件循环
        aweme_data = asyncio.run(download_with_f2(video_id))

        # 上传视频到飞书
        upload_result = upload_video_to_feishu(aweme_data, channel)
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
    """
    解析小红书笔记接口

    支持 GET 和 POST 请求
    参数：url - 小红书笔记链接（支持短链接、discovery、explore格式）
    """
    try:
        # 1. 获取请求参数
        if request.method == "GET":
            base_url = request.args.get("url", "").strip()

            # 特殊处理：如果 URL 参数中包含未编码的 &，Flask 会将其拆分为多个参数
            # 例如：url=...?source=webshare&xsec_token=xxx 会被拆分为 url=...?source=webshare 和 xsec_token=xxx
            # 需要检查是否有 xsec_token、xsec_source、xhsshare 等参数需要重新拼接
            if 'xiaohongshu.com' in base_url and '?' in base_url:
                # 检查是否有被拆分的查询参数
                extra_params = {}
                for key in ['xsec_token', 'xsec_source', 'xhsshare', 'source']:
                    if key in request.args and key not in base_url:
                        extra_params[key] = request.args.get(key)

                # 如果有额外的参数，重新拼接
                if extra_params:
                    # 手动拼接参数，避免 urlencode 对 = 进行编码
                    params_list = [f"{k}={v}" for k, v in extra_params.items()]
                    param_str = '&'.join(params_list)
                    # 如果 base_url 已经有查询参数，用 & 连接，否则用 ?
                    separator = '&' if '?' in base_url else '?'
                    base_url = base_url + separator + param_str
                    logging.info(f"重新组装 URL，添加参数: {list(extra_params.keys())}")
        else:
            payload = request.get_json(force=True, silent=True) or {}
            base_url = payload.get("url", "").strip()

        if not base_url:
            return jsonify({"ok": False, "error": "缺少必需参数 url"}), 400

        # 2. 解析并标准化链接
        note_id, xsec_token, url = extract_note_info_from_url(base_url, XHS_COOKIE)

        if not url or not note_id or not xsec_token:
            return jsonify({
                "ok": False,
                "error": "无法解析小红书链接，请检查链接格式（需要包含笔记ID和xsec_token）"
            }), 400

        logging.info(f"解析小红书链接: note_id={note_id}, url={url}")

        # 3. 根据模式解析笔记
        if XHS_MODE == 'api':
            result = parse_note_api_mode(url, XHS_COOKIE, DOWNLOAD_DIR)
        else:
            result = parse_note_web_mode(url, XHS_COOKIE, DOWNLOAD_DIR)

        # 4. 上传到飞书（如果解析成功）
        if result.get("ok") and isinstance(result.get("data"), list) and len(result["data"]) > 0:
            note_data = result["data"][0]
            feishu_result = upload_note_to_feishu(note_data)
            result["feishu"] = feishu_result

            # 如果飞书上传失败，整体标记为失败
            if not feishu_result.get("ok"):
                result["ok"] = False
                result["error"] = f"笔记解析成功，但上传到飞书失败: {feishu_result.get('error', '未知错误')}"

        # 根据结果决定状态码
        if result.get("ok"):
            # 成功时添加 success 字段
            result["success"] = True
            return jsonify(result), 200
        else:
            # 解析失败或上传失败，返回 500，不包含 success 字段
            return jsonify(result), 500
    except Exception as e:
        logging.error("parse_xhs_note failed: %s", e)
        traceback.print_exc()
        # 失败时不包含 success 字段
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {str(e)}"}), 500


@app.route("/xhs/parse_author", methods=["GET", "POST"])
def parse_xhs_author():
    """
    解析小红书作者信息接口

    支持 GET 和 POST 请求
    参数：url - 作者主页链接或包含链接的文本
    """
    try:
        # 1. 获取请求参数
        if request.method == "GET":
            base_url = request.args.get("url", "").strip()
        else:
            payload = request.get_json(force=True, silent=True) or {}
            base_url = payload.get("url", "").strip()

        if not base_url:
            return jsonify({"ok": False, "error": "缺少必需参数 url"}), 400

        logging.info(f"解析小红书作者: {base_url[:100]}")

        # 2. 解析作者信息
        from xhs_author_parser import parse_author
        result = parse_author(base_url, XHS_COOKIE)

        # 3. 如果解析成功，上传到飞书
        if result.get("ok") and result.get("data"):
            from xhs_author_uploader import upload_author_to_feishu
            author_data = result["data"]
            feishu_result = upload_author_to_feishu(author_data)
            result["feishu"] = feishu_result

            # 如果飞书上传失败，整体标记为失败
            if not feishu_result.get("ok"):
                result["ok"] = False
                result["error"] = f"作者信息解析成功，但上传到飞书失败: {feishu_result.get('error', '未知错误')}"

        # 根据结果决定状态码
        if result.get("ok"):
            # 成功时添加 success 字段
            result["success"] = True
            return jsonify(result), 200
        else:
            # 解析失败或上传失败，返回 500，不包含 success 字段
            return jsonify(result), 500

    except Exception as e:
        logging.error("parse_xhs_author failed: %s", e)
        traceback.print_exc()
        # 失败时不包含 success 字段
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {str(e)}"}), 500


@app.route("/xhs/parse_goods", methods=["GET", "POST"])
def parse_xhs_goods():
    """
    解析小红书商品信息接口

    支持 GET 和 POST 请求
    参数：url - 商品链接或包含链接的文本
    """
    try:
        # 1. 获取请求参数
        if request.method == "GET":
            base_url = request.args.get("url", "").strip()
        else:
            payload = request.get_json(force=True, silent=True) or {}
            base_url = payload.get("url", "").strip()

        if not base_url:
            return jsonify({"ok": False, "error": "缺少必需参数 url"}), 400

        logging.info(f"解析小红书商品: {base_url[:100]}")

        # 2. 解析商品信息
        from xhs_goods_parser import parse_goods
        result = parse_goods(base_url, XHS_COOKIE)

        # 3. 如果解析成功，上传到飞书
        if result.get("ok") and result.get("data"):
            from xhs_goods_uploader import upload_goods_to_feishu
            goods_data = result["data"]
            feishu_result = upload_goods_to_feishu(goods_data)
            result["feishu"] = feishu_result

            # 如果飞书上传失败，整体标记为失败
            if not feishu_result.get("ok"):
                result["ok"] = False
                result["error"] = f"商品信息解析成功，但上传到飞书失败: {feishu_result.get('error', '未知错误')}"

        # 根据结果决定状态码
        if result.get("ok"):
            # 成功时添加 success 字段
            result["success"] = True
            return jsonify(result), 200
        else:
            # 解析失败或上传失败，返回 500，不包含 success 字段
            return jsonify(result), 500

    except Exception as e:
        logging.error("parse_xhs_goods failed: %s", e)
        traceback.print_exc()
        # 失败时不包含 success 字段
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {str(e)}"}), 500


@app.route("/feishu/check_video_exists", methods=["GET", "POST"])
def check_video_exists():
    """
    检查视频在飞书多维表格中是否存在

    参数：
    - video_id: 视频ID（字符串）

    返回：
    - success: True 表示查询成功
    - exists: True/False 表示视频是否存在
    - record_id: 如果存在，返回记录ID
    """
    try:
        # 获取 video_id 参数（支持 GET 和 POST）
        if request.method == "GET":
            video_id = request.args.get('video_id', '').strip()
        else:
            video_id = request.json.get('video_id', '').strip() if request.is_json else request.form.get('video_id', '').strip()

        if not video_id:
            return jsonify({"ok": False, "error": "缺少必需参数 video_id"}), 400

        logging.info(f"检查视频是否存在: video_id={video_id}")

        # 获取飞书访问令牌
        import feishu_table as feishu
        access_token = feishu.get_tenant_access_token()

        # 查询 video_id 是否存在
        existing = feishu.search_record_by_video_id(video_id, access_token=access_token)

        if existing.get("total", 0) > 0:
            # 视频已存在
            record_id = existing["items"][0].get("record_id")
            logging.info(f"视频存在: video_id={video_id}, record_id={record_id}")

            return jsonify({
                "ok": True,
                "success": True,
                "exists": True,
                "video_id": video_id,
                "record_id": record_id
            }), 200
        else:
            # 视频不存在
            logging.info(f"视频不存在: video_id={video_id}")

            return jsonify({
                "ok": True,
                "success": True,
                "exists": False,
                "video_id": video_id
            }), 200

    except Exception as e:
        logging.error(f"check_video_exists failed: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {str(e)}"}), 500


@app.route("/feishu/upload_file", methods=["POST"])
def upload_file_to_feishu_table():
    """
    上传文件到飞书多维表格接口

    参数：
    - file: 文件（multipart/form-data）
    - video_id: 视频ID（字符串）

    返回：
    - success: True 表示成功
    - ok: True/False
    - record_id: 飞书记录ID
    - file_token: 文件token
    """
    try:
        # 1. 检查参数
        if 'file' not in request.files:
            return jsonify({"ok": False, "error": "缺少必需参数 file"}), 400

        if 'video_id' not in request.form:
            return jsonify({"ok": False, "error": "缺少必需参数 video_id"}), 400

        file = request.files['file']
        video_id = request.form.get('video_id', '').strip()

        if not video_id:
            return jsonify({"ok": False, "error": "video_id 不能为空"}), 400

        if file.filename == '':
            return jsonify({"ok": False, "error": "未选择文件"}), 400

        logging.info(f"上传文件到飞书: video_id={video_id}, filename={file.filename}")

        # 2. 获取飞书访问令牌并检查 video_id 是否已存在
        import feishu_table as feishu
        access_token = feishu.get_tenant_access_token()

        existing = feishu.search_record_by_video_id(video_id, access_token=access_token)

        if existing.get("total", 0) > 0:
            # 记录已存在，直接返回失败，不上传文件
            record_id = existing["items"][0].get("record_id")
            logging.info(f"video_id {video_id} 已存在，record_id: {record_id}")

            return jsonify({
                "ok": False,
                "error": f"video_id {video_id} 已存在，record_id: {record_id}"
            }), 400

        # 3. video_id 不存在，保存临时文件到项目 tmp 目录
        temp_dir = os.path.join(os.path.dirname(__file__), "tmp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file.filename)

        file.save(temp_path)
        logging.info(f"文件已保存到临时目录: {temp_path}")

        # 4. 上传文件到飞书云盘
        upload_result = feishu.upload_file_to_bitable(
            file_path=temp_path,
            file_name=file.filename,
            access_token=access_token
        )

        if not upload_result or not upload_result.get("file_token"):
            # 删除临时文件
            try:
                os.remove(temp_path)
            except:
                pass
            return jsonify({"ok": False, "error": "文件上传到飞书云盘失败"}), 500

        file_token = upload_result["file_token"]
        logging.info(f"文件上传成功，file_token: {file_token}")

        # 5. 创建新记录
        FEISHU_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "Pyw7bsxDiaSkKXsBwUqc9DH4n5c")
        FEISHU_TABLE_ID = os.getenv("FEISHU_TABLE_ID", "tblm8VXL99Bt9lcK")
        FEISHU_FIELD_ATTACHMENT = os.getenv("FEISHU_FIELD_ATTACHMENT", "视频")
        FEISHU_FIELD_VIDEO_ID = os.getenv("FEISHU_FIELD_VIDEO_ID", "video_id")

        fields = {
            FEISHU_FIELD_VIDEO_ID: str(video_id),
            FEISHU_FIELD_ATTACHMENT: [{"file_token": file_token, "name": file.filename,"type": "file"}]
        }

        record = feishu.create_record(
            fields,
            access_token=access_token,
            app_token=FEISHU_APP_TOKEN,
            table_id=FEISHU_TABLE_ID
        )

        # 删除临时文件
        try:
            os.remove(temp_path)
        except:
            pass

        if record:
            record_id = record.get("record_id")
            logging.info(f"成功创建飞书记录: {record_id}")
            return jsonify({
                "ok": True,
                "success": True,
                "record_id": record_id,
                "file_token": file_token,
                "video_id": video_id
            }), 200
        else:
            return jsonify({"ok": False, "error": "创建飞书记录失败"}), 500

    except Exception as e:
        logging.error(f"upload_file_to_feishu_table failed: {e}")
        traceback.print_exc()
        # 删除临时文件
        try:
            if 'temp_path' in locals():
                os.remove(temp_path)
        except:
            pass
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
