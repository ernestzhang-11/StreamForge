// const BACKEND_BASE_URL = "http://49.235.209.96:8080"; // 替换为你的服务器地址
const BACKEND_BASE_URL = "http://192.168.0.107:5000"; // 替换为你的服务器地址

function getBackendUrl(path) {
  return `${BACKEND_BASE_URL}${path}`;
}

async function callBackendUploadByPage(pageUrl, videoId) {
  console.log("[bg] callBackendUploadByPage:", { pageUrl, videoId, url: getBackendUrl("/feishu/upload_record") });
  const res = await fetch(getBackendUrl("/feishu/upload_record"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page_url: String(pageUrl), video_id: videoId ? String(videoId) : undefined })
  });
  let data;
  try {
    data = await res.json();
  } catch (e) {
    console.error("[bg] 后端返回非JSON或解析失败:", e);
    throw new Error(`后端响应解析失败: HTTP ${res.status}`);
  }
  if (!res.ok || !data?.ok) {
    console.error("[bg] 后端错误响应:", { status: res.status, data });
    throw new Error(data?.message || data?.error || `后端错误: HTTP ${res.status}`);
  }
  console.log("[bg] 上传成功:", data);
  return data;
}

async function processUpload({ pageUrl, videoId }) {
  if (!pageUrl || typeof pageUrl !== "string") {
    throw new Error("无效的页面链接: pageUrl 缺失或非法");
  }
  return await callBackendUploadByPage(pageUrl, videoId);
}

// Service Worker 启动日志
console.log("[bg] Service Worker started");

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  console.log("[bg] received msg:", msg);
  if (msg?.type === "UPLOAD_TO_FEISHU") {
    const payload = msg?.payload || {};
    (async () => {
      try {
        if (!payload?.pageUrl) {
          throw new Error("payload.pageUrl 缺失");
        }
        const result = await processUpload(payload);
        console.log("[bg] processUpload result:", result);
        // 透传服务端 message 与数据，前端据此提示
        sendResponse({ ok: true, message: result.message, data: result });
      } catch (e) {
        console.error("[bg] processUpload error:", e);
        sendResponse({ ok: false, message: e?.message || String(e), error: e?.message || String(e) });
      }
    })();
    // 异步响应
    return true;
  }
});