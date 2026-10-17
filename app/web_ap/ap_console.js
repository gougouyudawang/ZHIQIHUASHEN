const AP_API = "/v1/ap";

const state = {
  publicKey: "",
  currentAgentType: "octopus",
  dbItems: [],
};

const $ = (id) => document.getElementById(id);

function setDebug(data) {
  $("debugBox").textContent =
    typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

async function request(url, options = {}) {
  const r = await fetch(url, options);

  // 会话失效时统一送回登录页，避免界面停在一个永远拉不到数据的状态
  if (r.status === 401) {
    location.replace("/ap/login?next=" + encodeURIComponent(location.pathname));
    throw new Error("登录状态已失效");
  }

  const text = await r.text();

  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }

  if (!r.ok) {
    throw new Error(data.detail || data.error || `${r.status} ${r.statusText}`);
  }

  return data;
}

/* ---------- 登录身份显示与退出 ---------- */

(function initAuthBar() {
  const nameEl = $("userName");
  const roleEl = $("userRole");
  const avatarEl = document.querySelector(".user-chip-avatar");
  const btn = $("logoutBtn");

  request(`${AP_API}/me`)
    .then((data) => {
      const u = (data && data.user) || {};
      // 兼容两套字段名：后端已输出 username/display，早期版本返回的是 u/r/d
      const name = u.username || u.u || "";
      const role = u.display || u.d || "";
      if (nameEl) nameEl.textContent = name || "—";
      if (roleEl) roleEl.textContent = role || "—";
      if (avatarEl && name) avatarEl.textContent = name.charAt(0).toUpperCase();
    })
    .catch(() => {
      /* 未登录情形已由 request 统一跳转，这里无需额外处理 */
    });

  if (btn) {
    let busy = false;
    btn.addEventListener("click", async () => {
      if (busy) return;          // 连点会让第二次请求带着已吊销的令牌，无谓往返
      busy = true;
      btn.disabled = true;
      try {
        await request(`${AP_API}/logout`, { method: "POST" });
      } catch (e) {
        /* 无论登出接口成败，都回到登录页 */
      }
      location.replace("/ap/login");
    });
  }
})();

function shortText(v, len = 18) {
  const s = String(v ?? "");
  if (s.length <= len) return s;
  return s.slice(0, len) + "...";
}

function categoryName(agentType, index) {
  if (agentType === "openclaw") {
    const names = [
      "运行时",
      "网关",
      "人格",
      "Hooks",
      "Skills",
      "LLM",
      "知识",
      "渠道",
      "外观",
    ];
    return names[index] || `第 ${index + 1} 组`;
  }

  const names = ["功能", "输入", "推理", "知识", "输出", "外观"];
  return names[index] || `第 ${index + 1} 组`;
}

function labelZh(label) {
  const map = {
    "text-processing": "文本处理",
    "news-search": "新闻查询",
    "payment": "支付",
    "web-browsing": "联网搜索",

    "text": "文本",
    "voice": "语音",
    "image": "图像",

    "rag-openai": "RAG OpenAI",
    "rag-deepseek": "RAG DeepSeek",

    "local-memory": "本地记忆",
    "long-term-memory": "长期记忆",
    "knowledge-pro": "专业知识库",

    "speech": "语音输出",
    "video": "视频",
    "ppt": "PPT",

    "appearance-purple": "紫色",
    "appearance-blue": "蓝色",
    "appearance-pink": "粉色",
    "appearance-green": "绿色",

    "agent-openclaw": "OpenClaw",
    "openclaw": "OpenClaw",

    "hook-session-memory": "会话记忆",
    "hook-command-logger": "命令审计",
    "hook-bootstrap-files": "引导文件",
    "hook-boot-md": "启动脚本",

    "skill-weather": "天气 Skill",
    "skill-github": "GitHub Skill",
    "skill-desearch-web-search": "联网搜索 Skill",

    "llm-model": "大模型配置",
  };

  return map[label] || label || "未命名";
}

async function loadStatus() {
  try {
    const data = await request(`${AP_API}/status`);

    $("serviceStatus").textContent = data.success ? "在线" : "异常";
    $("recordCount").textContent = data.record_count ?? "-";
    $("agentTypes").textContent = (data.supported_agent_types || []).join(" / ");

    setDebug(data);
  } catch (e) {
    $("serviceStatus").textContent = "离线/异常";
    setDebug("读取 AP 状态失败：" + e.message);
  }
}

async function loadPublicKeys() {
  try {
    const data = await request(`${AP_API}/public_keys`);
    state.publicKey = data.ap_dlog_pk || "";
    $("publicKeyBox").textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    $("publicKeyBox").textContent = "读取 AP 公钥失败：" + e.message;
  }
}

async function loadCapabilities(agentType = state.currentAgentType) {
  state.currentAgentType = agentType;

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.agentType === agentType);
  });

  try {
    const data = await request(
      `${AP_API}/capabilities?agent_type=${encodeURIComponent(agentType)}`
    );

    renderCapabilities(data.cmm || [], agentType);
    setDebug(data);
  } catch (e) {
    $("capabilityGrid").innerHTML =
      `<div class="cap-card">读取能力矩阵失败：${escapeHtml(e.message)}</div>`;
  }
}

function renderCapabilities(cmm, agentType) {
  const grid = $("capabilityGrid");

  if (!Array.isArray(cmm) || cmm.length === 0) {
    grid.innerHTML = `<div class="cap-card">暂无能力矩阵</div>`;
    return;
  }

  grid.innerHTML = cmm
    .map((row, idx) => {
      const items = Array.isArray(row) ? row : [];

      const chips = items.length
        ? items
            .map((item) => {
              const label =
                item && typeof item === "object" ? item.label : String(item);
              const title = labelZh(label);
              return `<span class="chip" title="${escapeHtml(label)}">${escapeHtml(title)}</span>`;
            })
            .join("")
        : `<span class="chip empty">空</span>`;

      return `
        <div class="cap-card">
          <div class="cap-title">${escapeHtml(categoryName(agentType, idx))}</div>
          <div class="cap-items">${chips}</div>
        </div>
      `;
    })
    .join("");
}

async function loadDb() {
  try {
    const data = await request(`${AP_API}/db`);
    state.dbItems = data.items || [];

    $("recordCount").textContent = data.count ?? state.dbItems.length;
    renderDbTable(state.dbItems);
    setDebug(data);
  } catch (e) {
    $("dbTableBody").innerHTML =
      `<tr><td colspan="6">读取 AP DB 失败：${escapeHtml(e.message)}</td></tr>`;
  }
}

function renderDbTable(items) {
  const body = $("dbTableBody");

  if (!items.length) {
    body.innerHTML = `
      <tr>
        <td colspan="6">暂无 AP 签发/恢复记录。请先在 user 端完成“加载配置/提交配置”。</td>
      </tr>
    `;
    return;
  }

  body.innerHTML = items
    .map((it) => {
      const hid = String(it.hid || "");
      return `
        <tr>
          <td>
            <code title="${escapeHtml(hid)}">${escapeHtml(shortText(hid, 22))}</code>
          </td>
          <td>${escapeHtml(it.agent_type || "-")}</td>
          <td>
            <code title="${escapeHtml(it.CMI || "")}">${escapeHtml(shortText(it.CMI, 20))}</code>
          </td>
          <td>${escapeHtml(it.cmc_count ?? "-")}</td>
          <td>${escapeHtml(it.ts || "-")}</td>
          <td>
            <div class="row-actions">
              <button class="ghost-btn" onclick="viewRecord('${encodeURIComponent(hid)}')">详情</button>
              <button class="danger-btn" onclick="deleteRecord('${encodeURIComponent(hid)}')">删除</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function viewRecord(encodedHid) {
  const hid = decodeURIComponent(encodedHid);

  try {
    const data = await request(`${AP_API}/db/${encodeURIComponent(hid)}`);

    $("detailPanel").style.display = "block";
    $("detailBox").textContent = JSON.stringify(data, null, 2);

    setDebug(data);

    $("detailPanel").scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  } catch (e) {
    setDebug("读取记录详情失败：" + e.message);
  }
}

async function deleteRecord(encodedHid) {
  const hid = decodeURIComponent(encodedHid);

  if (!confirm(`确定删除 AP DB 记录？\n${hid}`)) {
    return;
  }

  try {
    const data = await request(`${AP_API}/db/${encodeURIComponent(hid)}`, {
      method: "DELETE",
    });

    setDebug(data);
    await loadDb();
  } catch (e) {
    setDebug("删除失败：" + e.message);
  }
}

async function refreshAll() {
  await loadStatus();
  await loadPublicKeys();
  await loadCapabilities(state.currentAgentType);
  await loadDb();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

window.viewRecord = viewRecord;
window.deleteRecord = deleteRecord;

document.addEventListener("DOMContentLoaded", () => {
  $("refreshAllBtn").addEventListener("click", refreshAll);
  $("refreshDbBtn").addEventListener("click", loadDb);

  $("copyPkBtn").addEventListener("click", async () => {
    if (!state.publicKey) {
      setDebug("当前没有可复制的 AP 公钥。");
      return;
    }

    try {
      await navigator.clipboard.writeText(state.publicKey);
      setDebug("AP 公钥已复制。");
    } catch (e) {
      setDebug("复制失败：" + e.message);
    }
  });

  $("closeDetailBtn").addEventListener("click", () => {
    $("detailPanel").style.display = "none";
  });

  $("clearDebugBtn").addEventListener("click", () => {
    $("debugBox").textContent = "暂无调试输出";
  });

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      loadCapabilities(btn.dataset.agentType);
    });
  });

  refreshAll();
});