"""前端驱动自动化测试 Agent 的 FastAPI 应用。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from test_agent.agent_service import (
    AgentHistoryResponse,
    AgentRunRequest,
    AgentRunResponse,
    get_agent_history,
    run_frontend_agent,
    stream_frontend_agent,
)


app = FastAPI(title="Playwright 自动化测试 Agent")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return FRONTEND_HTML


@app.post("/api/agent/run", response_model=AgentRunResponse)
def run_agent(payload: AgentRunRequest) -> AgentRunResponse:
    return run_frontend_agent(payload)


@app.post("/api/agent/run/stream")
def run_agent_stream(payload: AgentRunRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_frontend_agent(payload),
        media_type="application/x-ndjson; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/agent/history", response_model=AgentHistoryResponse)
def history(limit: int = 30) -> AgentHistoryResponse:
    return get_agent_history(limit=limit)


FRONTEND_HTML = """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>自动化测试 Agent</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f6f7f9;
        --panel: #ffffff;
        --text: #17202a;
        --muted: #5c6b7a;
        --line: #d9e0e7;
        --accent: #0f766e;
        --accent-dark: #115e59;
        --danger: #b42318;
        --ok: #027a48;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      header {
        height: 56px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 24px;
        border-bottom: 1px solid var(--line);
        background: var(--panel);
      }
      h1 {
        margin: 0;
        font-size: 18px;
        font-weight: 650;
      }
      main {
        display: grid;
        grid-template-columns: minmax(360px, 440px) minmax(0, 1fr);
        gap: 16px;
        padding: 16px;
        min-height: calc(100vh - 56px);
      }
      section {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px;
      }
      label {
        display: block;
        font-weight: 600;
        margin: 0 0 6px;
      }
      input, textarea {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 10px 11px;
        color: var(--text);
        background: #fff;
        font: inherit;
      }
      textarea {
        min-height: 160px;
        resize: vertical;
      }
      .field { margin-bottom: 14px; }
      .row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
      }
      .checks {
        display: flex;
        align-items: center;
        gap: 16px;
        margin: 12px 0 16px;
        color: var(--muted);
      }
      .checks label {
        display: flex;
        align-items: center;
        gap: 6px;
        margin: 0;
        font-weight: 500;
      }
      .checks input { width: auto; }
      button {
        width: 100%;
        border: 0;
        border-radius: 6px;
        padding: 11px 14px;
        color: #fff;
        background: var(--accent);
        font-weight: 650;
        cursor: pointer;
      }
      button:hover { background: var(--accent-dark); }
      button:disabled {
        cursor: wait;
        opacity: 0.7;
      }
      .status {
        margin-top: 12px;
        color: var(--muted);
      }
      .history {
        margin-top: 16px;
        border-top: 1px solid var(--line);
        padding-top: 14px;
      }
      .history-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }
      .link-btn {
        width: auto;
        padding: 0;
        color: var(--accent);
        background: transparent;
        font-weight: 600;
      }
      .link-btn:hover { background: transparent; color: var(--accent-dark); }
      .history-list {
        display: grid;
        gap: 8px;
        max-height: 260px;
        overflow: auto;
      }
      .history-item {
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 9px;
        background: #fbfcfd;
        cursor: pointer;
      }
      .history-item:hover { border-color: var(--accent); }
      .history-item strong {
        display: block;
        font-size: 13px;
        margin-bottom: 3px;
      }
      .history-meta {
        color: var(--muted);
        font-size: 12px;
      }
      .result-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
      }
      .progress {
        min-height: 150px;
        max-height: 240px;
        overflow: auto;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: #f8fafc;
        padding: 10px 12px;
        margin-bottom: 12px;
        font-family: Consolas, "SFMono-Regular", monospace;
        font-size: 12px;
        color: #243447;
      }
      .progress-line {
        padding: 3px 0;
        border-bottom: 1px dashed #e6ebf0;
      }
      .progress-line:last-child { border-bottom: 0; }
      .progress-node {
        color: var(--accent);
        font-weight: 700;
      }
      .badge {
        border-radius: 999px;
        padding: 4px 10px;
        background: #eef2f6;
        color: var(--muted);
        font-weight: 650;
      }
      .badge.ok { background: #ecfdf3; color: var(--ok); }
      .badge.fail { background: #fef3f2; color: var(--danger); }
      pre {
        min-height: 420px;
        white-space: pre-wrap;
        overflow: auto;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: #fbfcfd;
        padding: 14px;
        margin: 0;
      }
      @media (max-width: 860px) {
        main { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <header>
      <h1>自动化测试 Agent</h1>
      <span>LangGraph + browser-use</span>
    </header>
    <main>
      <section>
        <div class="field">
          <label for="url">目标页面 URL</label>
          <input id="url" value="https://www.litmedia.ai/" />
        </div>
        <div class="field">
          <label for="instruction">测试目标</label>
          <textarea id="instruction" placeholder="例如：测试页面某个按钮点击后是否进入预期页面"></textarea>
        </div>
        <div class="row">
          <div class="field">
            <label for="timeout">超时毫秒</label>
            <input id="timeout" type="number" value="15000" min="1000" max="120000" />
          </div>
          <div class="field">
            <label for="maxLinks">最大跳转数</label>
            <input id="maxLinks" type="number" value="30" min="1" max="500" />
          </div>
        </div>
        <div class="checks">
          <label><input id="headed" type="checkbox" checked /> 打开浏览器</label>
          <label><input id="crossOrigin" type="checkbox" /> 包含跨域链接</label>
        </div>
        <button id="runBtn">运行测试</button>
        <div id="status" class="status">等待输入</div>
        <div class="history">
          <div class="history-head">
            <strong>最近测试历史</strong>
            <button id="refreshHistory" class="link-btn" type="button">刷新</button>
          </div>
          <div id="historyList" class="history-list"></div>
        </div>
      </section>
      <section>
        <div class="result-head">
          <strong id="title">执行结果</strong>
          <span id="badge" class="badge">idle</span>
        </div>
        <div id="progress" class="progress">
          <div class="progress-line">等待开始...</div>
        </div>
        <pre id="output"></pre>
      </section>
    </main>
    <script>
      const runBtn = document.getElementById("runBtn");
      const statusEl = document.getElementById("status");
      const outputEl = document.getElementById("output");
      const progressEl = document.getElementById("progress");
      const badgeEl = document.getElementById("badge");
      const titleEl = document.getElementById("title");
      const historyListEl = document.getElementById("historyList");
      const refreshHistoryBtn = document.getElementById("refreshHistory");

      runBtn.addEventListener("click", async () => {
        const payload = {
          url: document.getElementById("url").value.trim(),
          instruction: document.getElementById("instruction").value.trim(),
          headed: document.getElementById("headed").checked,
          timeout_ms: Number(document.getElementById("timeout").value || 15000),
          max_links: Number(document.getElementById("maxLinks").value || 30),
          include_cross_origin: document.getElementById("crossOrigin").checked
        };

        runBtn.disabled = true;
        statusEl.textContent = "正在执行，浏览器会由后端打开...";
        badgeEl.className = "badge";
        badgeEl.textContent = "running";
        outputEl.textContent = "";
        progressEl.innerHTML = "";
        appendProgress("start", "开始提交流式任务...");

        try {
          const res = await fetch("/api/agent/run/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          if (!res.ok || !res.body) {
            throw new Error(`请求失败：HTTP ${res.status}`);
          }
          await readAgentStream(res.body);
        } catch (error) {
          badgeEl.className = "badge fail";
          badgeEl.textContent = "ERROR";
          outputEl.textContent = String(error);
          statusEl.textContent = "执行失败";
        } finally {
          runBtn.disabled = false;
        }
      });

      refreshHistoryBtn.addEventListener("click", loadHistory);

      async function loadHistory() {
        try {
          const res = await fetch("/api/agent/history?limit=10");
          const data = await res.json();
          const items = data.items || [];
          historyListEl.innerHTML = "";
          if (!items.length) {
            historyListEl.innerHTML = '<div class="history-meta">暂无历史记录</div>';
            return;
          }
          for (const item of items) {
            const el = document.createElement("div");
            el.className = "history-item";
            const status = item.success ? "PASS" : "FAIL";
            const time = item.created_at ? new Date(item.created_at).toLocaleString() : "";
            el.innerHTML = `
              <strong>${escapeHtml(status)} · ${escapeHtml(item.task_type || "未分类")}</strong>
              <div>${escapeHtml(item.goal || "")}</div>
              <div class="history-meta">${escapeHtml(item.url || "")} · ${escapeHtml(time)}</div>
            `;
            el.addEventListener("click", () => {
              document.getElementById("url").value = item.url || "";
              document.getElementById("instruction").value = item.goal || "";
              titleEl.textContent = `${item.report_title || "历史执行结果"} · ${item.route || ""}`;
              badgeEl.className = item.success ? "badge ok" : "badge fail";
              badgeEl.textContent = item.success ? "PASS" : "FAIL";
              outputEl.textContent = item.report_markdown || JSON.stringify(item, null, 2);
              statusEl.textContent = `已回填历史记录：${status}`;
            });
            historyListEl.appendChild(el);
          }
        } catch (error) {
          historyListEl.innerHTML = `<div class="history-meta">历史加载失败：${escapeHtml(String(error))}</div>`;
        }
      }

      async function readAgentStream(stream) {
        const reader = stream.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            handleStreamLine(line);
          }
        }
        if (buffer.trim()) {
          handleStreamLine(buffer);
        }
      }

      function handleStreamLine(line) {
        if (!line.trim()) return;
        const event = JSON.parse(line);
        if (event.type === "progress") {
          appendProgress(event.node || "progress", event.message || "");
          renderProgressDetail(event);
          statusEl.textContent = event.message || "执行中...";
          return;
        }
        if (event.type === "final") {
          const data = event.data || {};
          titleEl.textContent = `${data.title || "执行结果"} · ${data.route || ""}`;
          badgeEl.className = data.success ? "badge ok" : "badge fail";
          badgeEl.textContent = data.success ? "PASS" : "FAIL";
          outputEl.textContent = data.markdown || JSON.stringify(data, null, 2);
          statusEl.textContent = "执行完成";
          appendProgress("final", "最终报告已返回。");
          loadHistory();
          return;
        }
        if (event.type === "error") {
          badgeEl.className = "badge fail";
          badgeEl.textContent = "ERROR";
          outputEl.textContent = event.message || JSON.stringify(event, null, 2);
          statusEl.textContent = "执行失败";
          appendProgress("error", event.message || "流式执行失败");
        }
      }

      function renderProgressDetail(event) {
        if (event.test_plan && event.test_plan.length) {
          appendProgress("plan", event.test_plan.map((item, index) => `${index + 1}. ${item}`).join(" | "));
        }
        if (event.assertions && event.assertions.length) {
          appendProgress("assert", event.assertions.map((item, index) => `${index + 1}. ${item}`).join(" | "));
        }
        if (event.snapshot) {
          const s = event.snapshot;
          appendProgress("snapshot", `标题：${s.title || "无"}，可交互元素：${s.interactive_count || 0}，链接：${s.link_count || 0}`);
        }
        if (event.browser_use) {
          const b = event.browser_use;
          appendProgress("browser", `成功：${b.success}，步数：${b.steps}，错误数：${b.error_count}`);
        }
        if (event.evaluation) {
          appendProgress("evaluate", event.evaluation);
        }
      }

      function appendProgress(node, message) {
        const line = document.createElement("div");
        line.className = "progress-line";
        const time = new Date().toLocaleTimeString();
        line.innerHTML = `<span class="progress-node">[${escapeHtml(time)} ${escapeHtml(node)}]</span> ${escapeHtml(message)}`;
        progressEl.appendChild(line);
        progressEl.scrollTop = progressEl.scrollHeight;
      }

      function escapeHtml(value) {
        return String(value)
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#039;");
      }

      loadHistory();
    </script>
  </body>
</html>
"""
