# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StreamForge is a video content automation platform that crawls, downloads, and uploads videos from Douyin (抖音) and Xiaohongshu (小红书) to Feishu (飞书) multi-dimensional tables for content management. It consists of three major components: a Flask backend server, an automated Playwright-based crawler, and a Chrome extension.

## Architecture

### Core Components

1. **Flask Backend (`server/app.py`)**
   - Main API server exposing endpoints for video parsing and upload
   - Integrates with F2 library (Douyin downloader) and XHS-Downloader/Spider_XHS (Xiaohongshu)
   - Uploads videos and metadata to Feishu Bitable
   - Product name mapping service for e-commerce video classification

2. **Automated Crawler (`auto_craw/bit_playwright.py`)**
   - Uses BitBrowser (指纹浏览器) via Playwright for anti-detection
   - Monitors Douyin search results via XHR interception
   - Filters videos by recency (configurable via `RECENT_DAYS`)
   - Runs continuously on 30-minute intervals
   - Maintains upload/failure tracking in local text files

3. **Chrome Extension (`chrome_plugin/`)**
   - Provides UI for manual video upload to Feishu
   - Communicates with Flask backend via REST API

### External Integrations

- **Feishu Bitable API** (`server/feishu_table.py`): File upload (chunked for large files), record creation, and search
- **F2 Library**: Douyin video download and metadata extraction
- **XHS Integration**: Dual-mode system (see below)
- **BitBrowser API** (`auto_craw/bit_api.py`): Browser profile management

## XHS (Xiaohongshu) Integration

### URL Parser (`server/xhs_url_parser.py`)

Before parsing notes, all XHS URLs are normalized through the URL parser, which supports:

1. **Short links** (`xhslink.com`) - Requires cookie, follows redirects to get real URL
2. **Discovery format** (`/discovery/item/{note_id}?xsec_token=xxx`)
3. **Explore format** (`/explore/{note_id}?xsec_token=xxx`)
4. **Text with embedded links** - Extracts URL from surrounding text

All formats are normalized to: `https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}`

See `docs/XHS_URL_PARSER.md` for detailed documentation.

### Unified Download System (`server/xhs_downloader_util.py`)

After parsing note data (from either API or Web mode), media files are downloaded using a unified system:

- **Prevents file conflicts**: Each note saved to `{author}/{title}_{note_id}/`
- **Consistent naming**: `image_0.jpg`, `image_1.jpg`, `cover.jpg`, `video.mp4`
- **Standardized metadata**: `info.json` (machine-readable), `detail.txt` (human-readable)
- **Works with both modes**: API and Web mode data structures are normalized internally

See `docs/XHS_DOWNLOAD.md` for detailed documentation.

### Provider System

The codebase supports two modes for parsing Xiaohongshu notes, controlled by `XHS_MODE` environment variable:

### Mode Selection
- `XHS_MODE=web` (default): Uses bundled `xhs_downloader` library (web scraping)
- `XHS_MODE=api`: Uses Spider_XHS-style Web API client

### Provider Resolution (`server/xhs_provider.py`)
When `XHS_MODE=api`, the system tries two sources in order:
1. `SPIDER_XHS_PATH` env var → imports from specified path (or auto-detects `Spider_XHS/` submodule at project root)
2. Installed `apis.xhs_pc_apis` package → imports from site-packages

**Important**: API mode requires:
- `XHS_COOKIE` with valid `a1` token
- Node.js runtime + PyExecJS installed
- Valid `Spider_XHS/static/xhs_xs_xsc_56.js` signature script from upstream repo

## Common Commands

### Verify XHS Provider
```bash
make verify-provider
# or
python3 scripts/verify_xhs_provider.py
```

### Manage Spider_XHS as Git Submodule
```bash
make xhs-submodule-add          # Add as vendor/Spider_XHS
make xhs-submodule-update       # Update to latest
make xhs-submodule-pin REF=v1.0 # Pin to specific tag/commit
make xhs-submodule-status       # Show current state
```

### Run Flask Server
```bash
# Development
python server/app.py

# Production (with gunicorn)
gunicorn -c server/gunicorn_conf.py server.app:app
```

### Run Automated Crawler
```bash
python auto_craw/bit_playwright.py
```
Runs indefinitely with 30-minute intervals. Uses keywords from `auto_craw/keywords.txt`.

## Environment Variables

### Required
- `FEISHU_APP_ID`, `FEISHU_APP_SECRET`: Feishu app credentials
- `FEISHU_APP_TOKEN`, `FEISHU_TABLE_ID`: Douyin video Bitable coordinates
- `FEISHU_XHS_APP_TOKEN`, `FEISHU_XHS_TABLE_ID`: XHS note Bitable coordinates

### Optional
- `XHS_MODE`: `web` or `api` (default: `api`)
- `XHS_COOKIE`: Required for XHS API mode (must include `a1`)
- `SPIDER_XHS_PATH`: Path to Spider_XHS repo (auto-detects `Spider_XHS/` submodule if not set)
- `BACKEND_BASE_URL`: Flask server URL (default: `http://127.0.0.1:5000`)
- `BIT_BROWSER_ID`: BitBrowser profile ID
- `MAX_VIDEOS`: Maximum videos to collect per keyword (default: 200)
- `RECENT_DAYS`: Only process videos from last N days (default: 3)
- `DOWNLOAD_DIR`: Video download directory
- `PORT`: Flask server port (default: 5000)

## Key Workflows

### Douyin Video Upload Flow
1. Client sends `POST /feishu/upload_record` with `{"page_url": "..."}`
2. Server extracts `video_id` from URL
3. Check Feishu Bitable for existing record (by `video_id`)
4. If new: Download video using F2 library
5. Extract product info from `aweme_data.anchor_info`
6. Map product name using `server/product_mapping.json`
7. Upload video file to Feishu drive (chunked if >20MB)
8. Create Bitable record with video attachment + metadata
9. Record URL in `auto_craw/uploaded_urls.txt` (for crawler deduplication)

### XHS Note Upload Flow
1. Client sends `POST /xhs/parse_note?url=...`
2. Mode branching:
   - **Web mode**: `XHS-Downloader` parses page, downloads media to `DOWNLOAD_DIR/xhs/`
   - **API mode**: `Spider_XHS.XHS_Apis.get_note_info()` fetches structured JSON
3. Upload cover/images/video from local files (not remote URLs)
4. Parse timestamps from `发布时间` field (handles formats like `2024-01-01_12.30.45`)
5. Create XHS Bitable record with attachments

### Automated Crawler Operation
1. Load keywords from `auto_craw/keywords.txt`
2. For each keyword:
   - Open BitBrowser with saved cookies/fingerprint
   - Navigate to `https://www.douyin.com/search/{keyword}?type=general`
   - Intercept XHR responses (`search/single`, `search/item`)
   - Extract `aweme_id` + `create_time` from JSON responses
   - Apply "最新发布" filter and scroll to load more
   - Collect waterfall card IDs from DOM (`waterfall_item_*`)
   - Filter by `RECENT_DAYS` cutoff
3. Deduplicate against `uploaded_urls.txt` and `failed_urls.txt`
4. Upload via backend with 2-second throttle
5. Track results and sleep until next 30-minute cycle

## Product Mapping

`server/product_mapping.json` structure:
```json
{
  "product_name_mapping": {
    "关键词1": "映射值1",
    "关键词2": "映射值2"
  }
}
```

- File is reloaded every 30 seconds if modified
- Used in `upload_video_to_feishu()` to normalize product names
- When `channel=bit_playwright`, upload fails if no mapping match found

## File Tracking

- `auto_craw/uploaded_urls.txt`: Successfully uploaded video URLs (one per line)
- `auto_craw/failed_urls.txt`: Failed URLs with reason (tab-separated: `URL\tReason`)
- `auto_craw/keywords.txt`: Search keywords (one per line, `#` for comments)

## Important Implementation Details

### Asyncio Event Loop Handling
- Flask routes use `asyncio.run()` for F2/XHS async operations
- Crawler uses single `async_playwright()` context per keyword
- Event loop conflicts resolved by using `asyncio.run()` in synchronous Flask context

### Feishu File Upload
- Files >20MB use chunked upload (`_upload_large_file`)
- Files <20MB use single request (`_upload_small_file`)
- Retries with exponential backoff (max 3 attempts)
- Upload to `bitable_file` parent type for drive integration

### XHR Response Parsing (Crawler)
- Recursively walks JSON tree to find `aweme_info` or `aweme_list`
- Handles nested structures from different API endpoints
- Robust extraction of `aweme_id` and `create_time`
- Concurrent listening during scrolling to maximize collection

### BitBrowser Integration
- Connects via CDP (Chrome DevTools Protocol) websocket
- Reuses browser profile to maintain cookies/localStorage
- Closed after each keyword cycle to avoid resource leaks

## Updating Spider_XHS

The `Spider_XHS/` directory is a git submodule pointing to the upstream repository. To update:

```bash
# Update to latest version
git submodule update --remote Spider_XHS

# Or use Makefile
make xhs-submodule-update

# Pin to specific version
cd Spider_XHS
git checkout v1.0.0  # or commit hash
cd ..
git add Spider_XHS
git commit -m "Pin Spider_XHS to v1.0.0"
```

**Note**: The old `server/spider_xhs/` vendor directory is deprecated and ignored by git. All XHS API functionality now uses the `Spider_XHS/` submodule.

## Code Locations Reference

- Flask routes: `server/app.py`
- Feishu integration: `server/feishu_table.py`
- XHS URL parser: `server/xhs_url_parser.py` (handles short links, discovery/explore formats)
- XHS unified download: `server/xhs_downloader_util.py` (unified download for API/Web modes)
- XHS provider resolution: `server/xhs_provider.py`
- XHS upstream (submodule): `Spider_XHS/` (NOT `server/spider_xhs/`)
- Product mapping: `server/product_mapping_service.py`
- Crawler logic: `auto_craw/bit_playwright.py`
- BitBrowser API: `auto_craw/bit_api.py`
- Chrome extension: `chrome_plugin/background.js`
- Gunicorn config: `server/gunicorn_conf.py`
