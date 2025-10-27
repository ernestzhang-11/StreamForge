(() => {
  const BACKEND_BASE_URL = "http://localhost:5000"; // 替换为你的服务器地址
  const UPLOAD_ENDPOINT = "/feishu/upload_record";

  function extractVideoId(url) {
    const m = String(url).match(/\/video\/(\d+)/);
    return m ? m[1] : undefined;
  }

  async function backendUpload(pageUrl, videoId) {
    const url = `${BACKEND_BASE_URL}${UPLOAD_ENDPOINT}`;
    console.log("[content] Fallback fetch:", { url, pageUrl, videoId });
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_url: String(pageUrl), video_id: videoId ? String(videoId) : undefined })
    });
    let data;
    try { data = await res.json(); } catch (e) {
      console.error("[content] 后端响应解析失败:", e);
      throw new Error(`后端响应解析失败: HTTP ${res.status}`);
    }
    if (!res.ok || !data?.ok) {
      console.error("[content] 后端错误:", { status: res.status, data });
      throw new Error(data?.message || data?.error || `后端错误: HTTP ${res.status}`);
    }
    return data; // 直接返回服务端完整响应，包含 message/exists/records 等
  }

  function sendMessageAsync(message) {
    return new Promise((resolve, reject) => {
      try {
        chrome.runtime.sendMessage(message, (res) => {
          const lastErr = chrome.runtime.lastError;
          if (lastErr) {
            console.warn("[content] sendMessage lastError:", lastErr.message);
            reject(new Error(lastErr.message));
            return;
          }
          resolve(res);
        });
      } catch (e) {
        reject(e);
      }
    });
  }

  async function uploadFlow() {
    const pageUrl = location.href;
    const videoId = extractVideoId(pageUrl);
    console.log("[content] Upload click:", { pageUrl, videoId });

    // 优先消息到后台
    try {
      const resp = await sendMessageAsync({ type: "UPLOAD_TO_FEISHU", payload: { pageUrl, videoId } });
      console.log("[content] bg response:", resp);
      if (resp?.ok) {
        alert(resp?.message || "已成功上传");
      } else {
        alert("失败: " + (resp?.message || resp?.error || "未知错误"));
      }
      return;
    } catch (e) {
      console.warn("[content] 后台消息失败，改用后端直连:", e.message || String(e));
    }

    // 上下文失效或后台不可用时，直接请求后端
    try {
      const data = await backendUpload(pageUrl, videoId);
      console.log("[content] 直连后端成功:", data);
      alert(data?.message || "上传成功");
    } catch (e) {
      console.error("[content] 直连后端失败:", e);
      alert("上传失败: " + (e.message || String(e)));
    }
  }

  function ensureButton() {
    if (document.getElementById("__feishu_upload_btn")) return;
    const btn = document.createElement("button");
    btn.id = "__feishu_upload_btn";
    btn.textContent = "上传到飞书表格";
    btn.style.cssText = "position:fixed;right:20px;bottom:20px;z-index:999999;padding:8px 12px;background:#1677ff;color:#fff;border:none;border-radius:6px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.15)";
    btn.onclick = () => {
      // 防止上下文失效抛错
      Promise.resolve().then(uploadFlow).catch((e) => {
        console.error("[content] onclick error:", e);
        alert("点击失败: " + (e.message || String(e)));
      });
    };
    document.body.appendChild(btn);
    console.log("[content] Button injected");
  }

  // 初始注入
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureButton);
  } else {
    ensureButton();
  }

  // 监听单页应用路由变化，确保按钮存在
  const mo = new MutationObserver(() => ensureButton());
  mo.observe(document.documentElement, { childList: true, subtree: true });

  // 监听 history 路由切换
  ["pushState", "replaceState"].forEach((fn) => {
    const orig = history[fn];
    history[fn] = function() {
      const ret = orig.apply(this, arguments);
      setTimeout(ensureButton, 200);
      return ret;
    };
  });
  window.addEventListener("popstate", () => setTimeout(ensureButton, 200));
})();