"""前端驱动自动化测试 Agent 的 FastAPI 应用。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from test_agent.agent_service import AgentRunRequest, AgentRunResponse, run_frontend_agent


app = FastAPI(title="Playwright 自动化测试 Agent")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return FRONTEND_HTML


@app.post("/api/agent/run", response_model=AgentRunResponse)
def run_agent(payload: AgentRunRequest) -> AgentRunResponse:
    return run_frontend_agent(payload)


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
      .result-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
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
          <textarea id="instruction">测试一下这个页面的登录功能，登录凭证：lit511@qq.com、123456</textarea>
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
      </section>
      <section>
        <div class="result-head">
          <strong id="title">执行结果</strong>
          <span id="badge" class="badge">idle</span>
        </div>
        <pre id="output"></pre>
      </section>
    </main>
    <script>
      const runBtn = document.getElementById("runBtn");
      const statusEl = document.getElementById("status");
      const outputEl = document.getElementById("output");
      const badgeEl = document.getElementById("badge");
      const titleEl = document.getElementById("title");

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

        try {
          const res = await fetch("/api/agent/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          titleEl.textContent = `${data.title} · ${data.route}`;
          badgeEl.className = data.success ? "badge ok" : "badge fail";
          badgeEl.textContent = data.success ? "PASS" : "FAIL";
          outputEl.textContent = data.markdown || JSON.stringify(data, null, 2);
          statusEl.textContent = "执行完成";
        } catch (error) {
          badgeEl.className = "badge fail";
          badgeEl.textContent = "ERROR";
          outputEl.textContent = String(error);
          statusEl.textContent = "执行失败";
        } finally {
          runBtn.disabled = false;
        }
      });
    </script>
  </body>
</html>
"""
