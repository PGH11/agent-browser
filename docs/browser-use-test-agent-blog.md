---
title: "LangGraph + browser-use：一个自然语言驱动的自动化测试 Agent 架构设计"
date: 2026-05-18
tags:
  - AI Agent
  - browser-use
  - LangGraph
  - 自动化测试
summary: "一个基于 LangGraph 外层状态机和 browser-use 浏览器执行引擎的自动化测试 Agent 设计，重点记录 Agent 框架、节点职责、路由逻辑、状态流转和工程化踩坑。"
---

# LangGraph + browser-use：一个自然语言驱动的自动化测试 Agent 架构设计

> 这篇文章记录一次自动化测试 Agent 的实践：用户在前端输入目标 URL 和自然语言测试目标，后端通过 LangGraph 做外层 ReAct 编排，再交给 browser-use 驱动真实浏览器完成测试，最后生成中文 Markdown 测试报告。

本文配图：

- 正文图 1：整体架构图
- 正文图 2：LangGraph ReAct 状态机图
- 正文图 3：一次登录测试成功后的 Markdown 报告截图，可以使用实际运行页面截图补充。

## 为什么想做这个 Agent

传统 Web 自动化测试通常依赖固定脚本。比如一个登录测试脚本可能长这样：

```python
await page.goto("https://example.com")
await page.click("text=Login")
await page.fill("input[type=email]", "user@example.com")
await page.fill("input[type=password]", "password")
await page.click("button[type=submit]")
```

这种方式稳定、可控，很适合固定业务流程。但如果用户每次都想输入不同目标，比如：

```text
测试登录功能
测试顶部导航栏是否能跳转
测试 Create Video 按钮是否正常
测试 Pricing 页面能不能打开
```

那系统就需要具备更强的 Agent 能力：理解目标、规划动作、操作浏览器、观察结果、生成报告。

我想做的是一个更接近“前端可接入”的自动化测试 Agent：用户不用写代码，只需要在页面输入自然语言目标，AI 自动理解页面并执行浏览器操作。

最终目标是：

```text
输入：目标 URL + 测试目标
执行：真实浏览器自动操作
输出：中文测试报告 + 执行轨迹 + 错误信息 + 截图路径
```

## 最终方案

最终我采用了：

```text
FastAPI 前端/API
  -> LangGraph 外层 ReAct 状态机
  -> browser-use 浏览器自动化 Agent
  -> Playwright/Chromium 真实浏览器
  -> Markdown 测试报告
```

整体架构如下：

![整体架构图](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMjgwIiBoZWlnaHQ9IjcyMCIgdmlld0JveD0iMCAwIDEyODAgNzIwIiByb2xlPSJpbWciIGFyaWEtbGFiZWxsZWRieT0idGl0bGUgZGVzYyI+CiAgPHRpdGxlIGlkPSJ0aXRsZSI+6Ieq5Yqo5YyW5rWL6K+VIEFnZW50IOaVtOS9k+aetuaehOWbvjwvdGl0bGU+CiAgPGRlc2MgaWQ9ImRlc2MiPuWxleekuuWJjeerr+OAgUZhc3RBUEnjgIFMYW5nR3JhcGjjgIFicm93c2VyLXVzZeOAgea1j+iniOWZqOWSjOaKpeWRiui+k+WHuuS5i+mXtOeahOiwg+eUqOWFs+ezu+OAgjwvZGVzYz4KICA8ZGVmcz4KICAgIDxzdHlsZT4KICAgICAgLmJnIHsgZmlsbDogI2Y2ZjhmYjsgfQogICAgICAubGFuZSB7IGZpbGw6ICNmZmZmZmY7IHN0cm9rZTogI2Q4ZTBlYTsgc3Ryb2tlLXdpZHRoOiAyOyB9CiAgICAgIC5ib3ggeyBmaWxsOiAjZmZmZmZmOyBzdHJva2U6ICMxYjZmNjg7IHN0cm9rZS13aWR0aDogMi40OyByeDogMTA7IH0KICAgICAgLmJveDIgeyBmaWxsOiAjZWVmOGY2OyBzdHJva2U6ICMxYjZmNjg7IHN0cm9rZS13aWR0aDogMi40OyByeDogMTA7IH0KICAgICAgLmJveDMgeyBmaWxsOiAjZmZmN2U2OyBzdHJva2U6ICNhODY3MDA7IHN0cm9rZS13aWR0aDogMi40OyByeDogMTA7IH0KICAgICAgLnRpdGxlIHsgZm9udDogNzAwIDMwcHggIk1pY3Jvc29mdCBZYUhlaSIsICJQaW5nRmFuZyBTQyIsIEFyaWFsLCBzYW5zLXNlcmlmOyBmaWxsOiAjMTcyMDJhOyB9CiAgICAgIC5sYW5lVGl0bGUgeyBmb250OiA3MDAgMThweCAiTWljcm9zb2Z0IFlhSGVpIiwgIlBpbmdGYW5nIFNDIiwgQXJpYWwsIHNhbnMtc2VyaWY7IGZpbGw6ICM1OTY1NzU7IH0KICAgICAgLnRleHQgeyBmb250OiA3MDAgMjBweCAiTWljcm9zb2Z0IFlhSGVpIiwgIlBpbmdGYW5nIFNDIiwgQXJpYWwsIHNhbnMtc2VyaWY7IGZpbGw6ICMxNzIwMmE7IH0KICAgICAgLnN1YiB7IGZvbnQ6IDE1cHggIk1pY3Jvc29mdCBZYUhlaSIsICJQaW5nRmFuZyBTQyIsIEFyaWFsLCBzYW5zLXNlcmlmOyBmaWxsOiAjNTI2MDZkOyB9CiAgICAgIC5hcnJvdyB7IHN0cm9rZTogIzFmMjkzNzsgc3Ryb2tlLXdpZHRoOiAyLjQ7IGZpbGw6IG5vbmU7IG1hcmtlci1lbmQ6IHVybCgjYXJyb3doZWFkKTsgfQogICAgICAuYXJyb3dTb2Z0IHsgc3Ryb2tlOiAjNmI3MjgwOyBzdHJva2Utd2lkdGg6IDI7IGZpbGw6IG5vbmU7IG1hcmtlci1lbmQ6IHVybCgjYXJyb3doZWFkU29mdCk7IHN0cm9rZS1kYXNoYXJyYXk6IDggNjsgfQogICAgPC9zdHlsZT4KICAgIDxtYXJrZXIgaWQ9ImFycm93aGVhZCIgbWFya2VyV2lkdGg9IjEyIiBtYXJrZXJIZWlnaHQ9IjgiIHJlZlg9IjExIiByZWZZPSI0IiBvcmllbnQ9ImF1dG8iPgogICAgICA8cGF0aCBkPSJNMCwwIEwxMiw0IEwwLDggWiIgZmlsbD0iIzFmMjkzNyIvPgogICAgPC9tYXJrZXI+CiAgICA8bWFya2VyIGlkPSJhcnJvd2hlYWRTb2Z0IiBtYXJrZXJXaWR0aD0iMTIiIG1hcmtlckhlaWdodD0iOCIgcmVmWD0iMTEiIHJlZlk9IjQiIG9yaWVudD0iYXV0byI+CiAgICAgIDxwYXRoIGQ9Ik0wLDAgTDEyLDQgTDAsOCBaIiBmaWxsPSIjNmI3MjgwIi8+CiAgICA8L21hcmtlcj4KICA8L2RlZnM+CgogIDxyZWN0IGNsYXNzPSJiZyIgd2lkdGg9IjEyODAiIGhlaWdodD0iNzIwIi8+CiAgPHRleHQgY2xhc3M9InRpdGxlIiB4PSI2NCIgeT0iNjIiPuiHquWKqOWMlua1i+ivlSBBZ2VudCDmlbTkvZPmnrbmnoQ8L3RleHQ+CiAgPHRleHQgY2xhc3M9InN1YiIgeD0iNjQiIHk9IjkyIj7nlKjmiLfovpPlhaXoh6rnhLbor63oqIDmtYvor5Xnm67moIfvvIxMYW5nR3JhcGgg5YGa5aSW5bGC57yW5o6S77yMYnJvd3Nlci11c2Ug6amx5Yqo55yf5a6e5rWP6KeI5Zmo5omn6KGM77yM5pyA57uI6L6T5Ye6IE1hcmtkb3duIOaKpeWRiuOAgjwvdGV4dD4KCiAgPHJlY3QgY2xhc3M9ImxhbmUiIHg9IjUwIiB5PSIxMjUiIHdpZHRoPSIxMTgwIiBoZWlnaHQ9IjEyOCIgcng9IjE0Ii8+CiAgPHRleHQgY2xhc3M9ImxhbmVUaXRsZSIgeD0iNzIiIHk9IjE1NSI+5Lqk5LqS5bGCPC90ZXh0PgogIDxyZWN0IGNsYXNzPSJib3giIHg9IjE2MCIgeT0iMTY1IiB3aWR0aD0iMjIwIiBoZWlnaHQ9IjY0Ii8+CiAgPHRleHQgY2xhc3M9InRleHQiIHg9IjIxMCIgeT0iMTk1Ij7liY3nq6/pobXpnaI8L3RleHQ+CiAgPHRleHQgY2xhc3M9InN1YiIgeD0iMTkwIiB5PSIyMTgiPlVSTCArIOiHqueEtuivreiogOebruaghzwvdGV4dD4KICA8cmVjdCBjbGFzcz0iYm94IiB4PSI1MDAiIHk9IjE2NSIgd2lkdGg9IjIyMCIgaGVpZ2h0PSI2NCIvPgogIDx0ZXh0IGNsYXNzPSJ0ZXh0IiB4PSI1NjUiIHk9IjE5NSI+RmFzdEFQSTwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic3ViIiB4PSI1MzUiIHk9IjIxOCI+UE9TVCAvYXBpL2FnZW50L3J1bjwvdGV4dD4KICA8cmVjdCBjbGFzcz0iYm94IiB4PSI4NDAiIHk9IjE2NSIgd2lkdGg9IjIyMCIgaGVpZ2h0PSI2NCIvPgogIDx0ZXh0IGNsYXNzPSJ0ZXh0IiB4PSI4OTgiIHk9IjE5NSI+5pyN5Yqh5bGCPC90ZXh0PgogIDx0ZXh0IGNsYXNzPSJzdWIiIHg9Ijg3NSIgeT0iMjE4Ij7mnoTpgKAgVGVzdFJlcXVlc3Q8L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJsYW5lIiB4PSI1MCIgeT0iMjg0IiB3aWR0aD0iMTE4MCIgaGVpZ2h0PSIxNDYiIHJ4PSIxNCIvPgogIDx0ZXh0IGNsYXNzPSJsYW5lVGl0bGUiIHg9IjcyIiB5PSIzMTQiPue8luaOkuWxgjwvdGV4dD4KICA8cmVjdCBjbGFzcz0iYm94MiIgeD0iMTYwIiB5PSIzMzIiIHdpZHRoPSIyMjAiIGhlaWdodD0iNzAiLz4KICA8dGV4dCBjbGFzcz0idGV4dCIgeD0iMjE4IiB5PSIzNjIiPkxhbmdHcmFwaDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic3ViIiB4PSIxOTQiIHk9IjM4NiI+5aSW5bGCIFJlQWN0IOeKtuaAgeacujwvdGV4dD4KICA8cmVjdCBjbGFzcz0iYm94MiIgeD0iNTAwIiB5PSIzMzIiIHdpZHRoPSIyMjAiIGhlaWdodD0iNzAiLz4KICA8dGV4dCBjbGFzcz0idGV4dCIgeD0iNTUyIiB5PSIzNjIiPuiKgueCueS4jui3r+eUsTwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic3ViIiB4PSI1MjYiIHk9IjM4NiI+UmVhc29uIC8gUGxhbiAvIEFjdDwvdGV4dD4KICA8cmVjdCBjbGFzcz0iYm94MiIgeD0iODQwIiB5PSIzMzIiIHdpZHRoPSIyMjAiIGhlaWdodD0iNzAiLz4KICA8dGV4dCBjbGFzcz0idGV4dCIgeD0iOTAwIiB5PSIzNjIiPueKtuaAgeWvueixoTwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic3ViIiB4PSI4ODUiIHk9IjM4NiI+VGVzdEFnZW50U3RhdGU8L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJsYW5lIiB4PSI1MCIgeT0iNDYxIiB3aWR0aD0iMTE4MCIgaGVpZ2h0PSIxMjgiIHJ4PSIxNCIvPgogIDx0ZXh0IGNsYXNzPSJsYW5lVGl0bGUiIHg9IjcyIiB5PSI0OTEiPuaJp+ihjOWxgjwvdGV4dD4KICA8cmVjdCBjbGFzcz0iYm94MyIgeD0iMTYwIiB5PSI1MDgiIHdpZHRoPSIyMjAiIGhlaWdodD0iNjQiLz4KICA8dGV4dCBjbGFzcz0idGV4dCIgeD0iMjA3IiB5PSI1MzgiPmJyb3dzZXItdXNlPC90ZXh0PgogIDx0ZXh0IGNsYXNzPSJzdWIiIHg9IjIwMCIgeT0iNTYxIj7mtY/op4jlmajmiafooYwgQWdlbnQ8L3RleHQ+CiAgPHJlY3QgY2xhc3M9ImJveDMiIHg9IjUwMCIgeT0iNTA4IiB3aWR0aD0iMjIwIiBoZWlnaHQ9IjY0Ii8+CiAgPHRleHQgY2xhc3M9InRleHQiIHg9IjU2OCIgeT0iNTM4Ij7mqKHlnos8L3RleHQ+CiAgPHRleHQgY2xhc3M9InN1YiIgeD0iNTQwIiB5PSI1NjEiPuinhuiniSArIOe7k+aehOWMlui+k+WHujwvdGV4dD4KICA8cmVjdCBjbGFzcz0iYm94MyIgeD0iODQwIiB5PSI1MDgiIHdpZHRoPSIyMjAiIGhlaWdodD0iNjQiLz4KICA8dGV4dCBjbGFzcz0idGV4dCIgeD0iOTAwIiB5PSI1MzgiPuecn+Wunua1j+iniOWZqDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic3ViIiB4PSI4ODUiIHk9IjU2MSI+54K55Ye7IC8g6L6T5YWlIC8g562J5b6FPC90ZXh0PgoKICA8cmVjdCBjbGFzcz0iYm94IiB4PSI1MDAiIHk9IjYyNiIgd2lkdGg9IjIyMCIgaGVpZ2h0PSI2NCIvPgogIDx0ZXh0IGNsYXNzPSJ0ZXh0IiB4PSI1NTIiIHk9IjY1NiI+5rWL6K+V5oql5ZGKPC90ZXh0PgogIDx0ZXh0IGNsYXNzPSJzdWIiIHg9IjUzNSIgeT0iNjc5Ij5NYXJrZG93biArIOaIquWbvui3r+W+hDwvdGV4dD4KCiAgPHBhdGggY2xhc3M9ImFycm93IiBkPSJNMzgwIDE5NyBINTAwIi8+CiAgPHBhdGggY2xhc3M9ImFycm93IiBkPSJNNzIwIDE5NyBIODQwIi8+CiAgPHBhdGggY2xhc3M9ImFycm93IiBkPSJNOTUwIDIyOSBWMzMyIi8+CiAgPHBhdGggY2xhc3M9ImFycm93IiBkPSJNODQwIDM2NyBINzIwIi8+CiAgPHBhdGggY2xhc3M9ImFycm93IiBkPSJNNTAwIDM2NyBIMzgwIi8+CiAgPHBhdGggY2xhc3M9ImFycm93IiBkPSJNMjcwIDQwMiBWNTA4Ii8+CiAgPHBhdGggY2xhc3M9ImFycm93IiBkPSJNMzgwIDU0MCBINTAwIi8+CiAgPHBhdGggY2xhc3M9ImFycm93IiBkPSJNNzIwIDU0MCBIODQwIi8+CiAgPHBhdGggY2xhc3M9ImFycm93IiBkPSJNOTUwIDU3MiBDOTUwIDYzMCA3ODAgNjU4IDcyMCA2NTgiLz4KICA8cGF0aCBjbGFzcz0iYXJyb3ciIGQ9Ik01MDAgNjU4IEM0MjAgNjUwIDI3MCA2MTAgMjcwIDU3MiIvPgogIDxwYXRoIGNsYXNzPSJhcnJvd1NvZnQiIGQ9Ik02MTAgNjI2IFY0MDIiLz4KPC9zdmc+Cg==)

```mermaid
flowchart TD
    A["前端页面<br/>输入 URL 和自然语言测试目标"] --> B["FastAPI<br/>POST /api/agent/run"]
    B --> C["LangGraph 外层 ReAct 状态机"]
    C --> D["route_request<br/>检查请求是否可执行"]

    D -->|"有效请求"| E["analyze_goal<br/>Reason: 分析任务类型"]
    E --> F["plan_browser_action<br/>Plan: 生成测试计划"]
    F --> G["browser_use<br/>Act: 调用 browser-use"]
    G --> H["真实浏览器<br/>点击、输入、等待、跳转"]
    H --> I["BrowserUseResult<br/>Observe: 整理执行历史"]
    I --> J["evaluate_result<br/>Evaluate: 外层复核"]
    J --> K["write_report<br/>生成 Markdown 报告"]

    D -->|"无效请求"| L["reject_request<br/>拒绝执行"]
    L --> K

    K --> M["前端展示结果"]
```

这里有一个关键设计：我没有让 LangGraph 直接操作浏览器，而是把它作为外层状态机。

LangGraph 负责：

- 判断请求是否合法
- 分析用户目标
- 生成测试计划
- 调用 browser-use
- 复核 browser-use 的结果
- 输出最终报告

browser-use 负责：

- 打开浏览器
- 观察页面
- 识别按钮、输入框、弹窗、链接
- 执行点击、输入、等待、跳转
- 汇总真实执行结果

这样职责比较清晰。外层 Agent 负责“测试流程”，内层 browser-use 负责“浏览器操作”。

## Agent 框架设计

这个 Agent 分成四层：

```text
交互层：FastAPI + 前端页面
编排层：LangGraph 外层状态机
执行层：browser-use Agent
模型层：OpenAI/Ark 兼容模型
```

每一层只做自己该做的事。

| 层级  | 主要职责                                      | 对应文件                                                      |
| --- | ----------------------------------------- | --------------------------------------------------------- |
| 交互层 | 接收 URL、自然语言目标、超时、有头模式等参数，并展示报告            | `test_agent/web_app.py`                                   |
| 服务层 | 把前端请求转换成内部 `TestRequest`，调用 LangGraph     | `test_agent/agent_service.py`                             |
| 编排层 | 通过节点和路由控制 Agent 流程                        | `test_agent/graph/builder.py`、`test_agent/graph/nodes.py` |
| 执行层 | 调用 browser-use 打开浏览器、观察页面、执行动作            | `test_agent/browser_use_runner.py`                        |
| 状态层 | 定义请求、结果、报告和全局状态结构                         | `test_agent/models.py`                                    |
| 配置层 | 管理模型配置、browser-use 工作目录、LangSmith tracing | `test_agent/settings.py`                                  |

从职责上看，LangGraph 是“主控 Agent”，browser-use 是“浏览器执行 Agent”。主控 Agent 不直接点击页面，而是负责把任务拆清楚、把状态传下去、把结果收回来。

```mermaid
flowchart LR
    A["用户自然语言目标"] --> B["TestRequest"]
    B --> C["LangGraph 主控 Agent"]
    C --> D["browser-use 执行 Agent"]
    D --> E["真实浏览器"]
    E --> F["AgentHistoryList"]
    F --> G["BrowserUseResult"]
    G --> H["Report"]
    H --> I["前端 Markdown 展示"]
```

## browser-use 接入方式

在这个项目里，我没有把 browser-use 当成一个简单的 Playwright 替代品，而是把它放在执行层，专门负责“真实浏览器里的多步操作”。外层的 LangGraph 负责判断任务、生成计划和收口报告；browser-use 只在 `browser_use` 节点里被调用。

实际链路是：

```text
前端表单
  -> AgentRunRequest
  -> TestRequest
  -> LangGraph 生成 browser_instruction
  -> browser-use Agent(task=browser_instruction)
  -> AgentHistoryList
  -> BrowserUseResult
  -> Markdown Report
```

前端传进来的数据结构是 `AgentRunRequest`：

```python
class AgentRunRequest(BaseModel):
    url: str
    instruction: str
    headed: bool = True
    timeout_ms: int
    max_candidates: int = 120
    max_links: int = 50
    include_cross_origin: bool = False
```

服务层会把它转换成内部的 `TestRequest`：

```python
request = TestRequest(
    base_url=payload.url,
    goal=payload.instruction,
    headed=payload.headed,
    browser=DEFAULT_BROWSER,
    timeout_ms=payload.timeout_ms,
    max_candidates=payload.max_candidates,
    mode="auto",
    max_links=payload.max_links,
    same_origin_only=not payload.include_cross_origin,
)
```

这里要注意一点：我传给 browser-use 的核心输入不是一个业务 JSON，而是一段整理过的任务文本。`plan_browser_action` 会先把用户目标、任务类型、测试计划和执行要求合并成 `browser_instruction`，然后在 `browser_use` 节点里重新写回 `TestRequest.goal`，最后交给 browser-use。

真正创建 browser-use Agent 的代码集中在 `test_agent/browser_use_runner.py`：

```python
agent = Agent(
    task=_build_task(request),
    llm=llm,
    browser_profile=profile,
    use_vision=True,
    step_timeout=max(30, int(request.timeout_ms / 1000)),
    max_failures=3,
    source="langchain1-browser-use",
)

history = await agent.run(max_steps=40)
```

这里几个参数比较关键：

| 参数 | 作用 |
| --- | --- |
| `task` | 传给 browser-use 的自然语言任务说明 |
| `llm` | OpenAI/Ark 兼容模型配置 |
| `browser_profile` | 浏览器运行目录、下载目录、trace 目录、有头/无头模式 |
| `use_vision=True` | 允许模型结合页面截图理解按钮、弹窗和复杂 UI |
| `step_timeout` | 单步操作超时时间 |
| `max_steps=40` | 最多执行 40 步浏览器动作 |

`_build_task()` 会把内部请求包装成更明确的浏览器测试任务。它包含目标页面、用户目标和执行约束，例如：

```text
目标页面：{request.base_url}
用户测试目标：{request.goal}

请你作为浏览器自动化测试 Agent 完成任务：
1. 打开目标页面。
2. 根据用户目标自主判断需要点击、输入、等待或检查的页面元素。
3. 如果目标涉及导航、跳转、登录、表单或按钮，请真实操作浏览器验证。
4. 不要编造结果。
5. 在最终 result 字段里用中文总结测试结果、执行步骤、失败原因和最终 URL。
```

同时我在任务里显式加了输出约束：

```text
必须严格遵守 browser-use 系统要求的 AgentOutput JSON 格式；
不要在 JSON 外输出中文说明、Markdown 或普通文本。
```

原因是 browser-use 内部每一步都需要模型返回它自己的 `AgentOutput` 结构。这个结构不是我在业务代码里定义的，而是 browser-use 自己用来表示“下一步要点击、输入、等待还是完成”的动作 JSON。如果模型直接返回一段中文总结，browser-use 就无法解析下一步动作。

所以这个项目对“执行过程中的模型输出”是有限制的：默认优先启用结构化输出。

```python
ChatOpenAI(
    model=OPENAI_MODEL,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    temperature=0,
    dont_force_structured_output=not force_structured_output,
    add_schema_to_system_prompt=not force_structured_output,
)
```

默认配置是：

```python
BROWSER_USE_FORCE_STRUCTURED_OUTPUT = os.getenv("BROWSER_USE_FORCE_STRUCTURED_OUTPUT", "1") != "0"
```

也就是说，默认先让模型通过 `json_schema` 按 browser-use 要求返回结构化 `AgentOutput`。如果兼容模型明确不支持 `json_schema`，代码会自动降级到 prompt schema 模式：

```text
优先使用 json_schema 强制模型返回 AgentOutput JSON。
如果模型接口不支持 json_schema，再用提示词要求模型按 schema 输出。
```

browser-use 执行完后返回的是 `AgentHistoryList` 一类的历史对象。前端不直接消费这个对象，我会把它规整成自己的 `BrowserUseResult`：

```python
class BrowserUseResult(BaseModel):
    success: bool = False
    final_result: str = ""
    errors: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    steps: int = 0
    duration_seconds: float | None = None
```

规整逻辑会提取：

```text
是否成功
最终总结
错误列表
访问过的 URL
截图路径
执行步数
耗时
```

这样做的好处是，browser-use 内部可以继续负责复杂的浏览器动作，而我的业务层只依赖一个稳定的结果协议。后续如果要增加历史报告、截图归档、失败重试或人工复核，也都可以围绕 `BrowserUseResult` 和 `Report` 扩展。

## 状态模型

状态机里最重要的是 `TestAgentState`。它是所有节点之间传递的任务单。

```python
class TestAgentState(TypedDict):
    request: TestRequest
    route: Literal["browser_use", "reject"]
    route_reason: str
    task_type: str
    test_plan: list[str]
    browser_instruction: str
    observations: list[str]
    evaluation: str
    browser_use_result: BrowserUseResult
    report: Report
    errors: list[str]
```

这个状态对象里有几类信息：

| 字段                    | 类型   | 作用                             |
| --------------------- | ---- | ------------------------------ |
| `request`             | 输入   | 用户传入的 URL、测试目标、浏览器配置           |
| `route`               | 路由   | 决定后续走 browser-use 还是 reject    |
| `route_reason`        | 路由说明 | 记录为什么选择这条路                     |
| `task_type`           | 任务分析 | 登录、导航、表单、通用页面行为等               |
| `test_plan`           | 计划   | 外层 Agent 生成的测试步骤               |
| `browser_instruction` | 执行指令 | 传给 browser-use 的完整任务说明         |
| `observations`        | 观察轨迹 | 记录 Reason、Plan、Act、Evaluate 过程 |
| `evaluation`          | 外层评估 | 对 browser-use 执行结果的复核          |
| `browser_use_result`  | 执行结果 | browser-use 返回并规整后的结果          |
| `report`              | 输出   | 最终给前端展示的 Markdown 报告           |
| `errors`              | 错误   | 外层流程捕获到的问题                     |

这里的设计重点是：每个节点只改自己负责的字段。

比如 `analyze_goal` 只负责写入 `task_type` 和 `test_plan`；`browser_use` 只负责写入 `browser_use_result`；`evaluate_result` 只负责写入 `evaluation`。

这种状态设计会让后续扩展更容易。比如要增加“失败重试”，只需要在状态里增加 `retry_count`，再在 `evaluate_result` 后加一个条件路由。

## 节点设计

当前状态机不是只有“执行”和“拒绝”两条路，而是增加了外层 ReAct 逻辑。

![LangGraph ReAct 状态机图](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMjgwIiBoZWlnaHQ9Ijc2MCIgdmlld0JveD0iMCAwIDEyODAgNzYwIiByb2xlPSJpbWciIGFyaWEtbGFiZWxsZWRieT0idGl0bGUgZGVzYyI+CiAgPHRpdGxlIGlkPSJ0aXRsZSI+TGFuZ0dyYXBoIFJlQWN0IOeKtuaAgeacuua1gei9rOWbvjwvdGl0bGU+CiAgPGRlc2MgaWQ9ImRlc2MiPuWxleekuiByb3V0ZV9yZXF1ZXN044CBYW5hbHl6ZV9nb2Fs44CBcGxhbl9icm93c2VyX2FjdGlvbuOAgWJyb3dzZXJfdXNl44CBZXZhbHVhdGVfcmVzdWx044CBcmVqZWN0X3JlcXVlc3Qg5ZKMIHdyaXRlX3JlcG9ydCDnmoTnirbmgIHmtYHovazjgII8L2Rlc2M+CiAgPGRlZnM+CiAgICA8c3R5bGU+CiAgICAgIC5iZyB7IGZpbGw6ICNmN2Y4ZmI7IH0KICAgICAgLnRpdGxlIHsgZm9udDogNzAwIDMwcHggIk1pY3Jvc29mdCBZYUhlaSIsICJQaW5nRmFuZyBTQyIsIEFyaWFsLCBzYW5zLXNlcmlmOyBmaWxsOiAjMTcyMDJhOyB9CiAgICAgIC5zdWIgeyBmb250OiAxNXB4ICJNaWNyb3NvZnQgWWFIZWkiLCAiUGluZ0ZhbmcgU0MiLCBBcmlhbCwgc2Fucy1zZXJpZjsgZmlsbDogIzUyNjA2ZDsgfQogICAgICAubm9kZSB7IGZpbGw6ICNmZmZmZmY7IHN0cm9rZTogIzFiNmY2ODsgc3Ryb2tlLXdpZHRoOiAyLjQ7IHJ4OiAxMjsgfQogICAgICAubm9kZUFjY2VudCB7IGZpbGw6ICNlZWY4ZjY7IHN0cm9rZTogIzFiNmY2ODsgc3Ryb2tlLXdpZHRoOiAyLjQ7IHJ4OiAxMjsgfQogICAgICAubm9kZVdhcm4geyBmaWxsOiAjZmZmNGU2OyBzdHJva2U6ICNhODY3MDA7IHN0cm9rZS13aWR0aDogMi40OyByeDogMTI7IH0KICAgICAgLm5vZGVFbmQgeyBmaWxsOiAjZjBmNGZmOyBzdHJva2U6ICMzZjVmYmY7IHN0cm9rZS13aWR0aDogMi40OyByeDogMTI7IH0KICAgICAgLmxhYmVsIHsgZm9udDogNzAwIDE5cHggIk1pY3Jvc29mdCBZYUhlaSIsICJQaW5nRmFuZyBTQyIsIEFyaWFsLCBzYW5zLXNlcmlmOyBmaWxsOiAjMTcyMDJhOyB9CiAgICAgIC5yb2xlIHsgZm9udDogNzAwIDE0cHggIk1pY3Jvc29mdCBZYUhlaSIsICJQaW5nRmFuZyBTQyIsIEFyaWFsLCBzYW5zLXNlcmlmOyBmaWxsOiAjMWI2ZjY4OyB9CiAgICAgIC5zbWFsbCB7IGZvbnQ6IDE0cHggIk1pY3Jvc29mdCBZYUhlaSIsICJQaW5nRmFuZyBTQyIsIEFyaWFsLCBzYW5zLXNlcmlmOyBmaWxsOiAjNTI2MDZkOyB9CiAgICAgIC5lZGdlIHsgc3Ryb2tlOiAjMWYyOTM3OyBzdHJva2Utd2lkdGg6IDIuNDsgZmlsbDogbm9uZTsgbWFya2VyLWVuZDogdXJsKCNhcnJvd2hlYWQpOyB9CiAgICAgIC5yZWplY3QgeyBzdHJva2U6ICNhODY3MDA7IHN0cm9rZS13aWR0aDogMi40OyBmaWxsOiBub25lOyBtYXJrZXItZW5kOiB1cmwoI2Fycm93aGVhZFdhcm4pOyB9CiAgICAgIC5ub3RlIHsgZmlsbDogI2ZmZmZmZjsgc3Ryb2tlOiAjZDhlMGVhOyBzdHJva2Utd2lkdGg6IDEuODsgcng6IDEwOyB9CiAgICA8L3N0eWxlPgogICAgPG1hcmtlciBpZD0iYXJyb3doZWFkIiBtYXJrZXJXaWR0aD0iMTIiIG1hcmtlckhlaWdodD0iOCIgcmVmWD0iMTEiIHJlZlk9IjQiIG9yaWVudD0iYXV0byI+CiAgICAgIDxwYXRoIGQ9Ik0wLDAgTDEyLDQgTDAsOCBaIiBmaWxsPSIjMWYyOTM3Ii8+CiAgICA8L21hcmtlcj4KICAgIDxtYXJrZXIgaWQ9ImFycm93aGVhZFdhcm4iIG1hcmtlcldpZHRoPSIxMiIgbWFya2VySGVpZ2h0PSI4IiByZWZYPSIxMSIgcmVmWT0iNCIgb3JpZW50PSJhdXRvIj4KICAgICAgPHBhdGggZD0iTTAsMCBMMTIsNCBMMCw4IFoiIGZpbGw9IiNhODY3MDAiLz4KICAgIDwvbWFya2VyPgogIDwvZGVmcz4KCiAgPHJlY3QgY2xhc3M9ImJnIiB3aWR0aD0iMTI4MCIgaGVpZ2h0PSI3NjAiLz4KICA8dGV4dCBjbGFzcz0idGl0bGUiIHg9IjY0IiB5PSI2MiI+TGFuZ0dyYXBoIFJlQWN0IOeKtuaAgeacuua1gei9rOWbvjwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic3ViIiB4PSI2NCIgeT0iOTIiPuacieaViOivt+axgui/m+WFpSBSZWFzb27jgIFQbGFu44CBQWN044CBRXZhbHVhdGUg5Li76Lev5b6E77yb5peg5pWI6K+35rGC6L+b5YWlIHJlamVjdF9yZXF1ZXN0IOWuieWFqOWHuuWPo+OAgjwvdGV4dD4KCiAgPHJlY3QgY2xhc3M9Im5vZGVFbmQiIHg9IjgwIiB5PSIxNjAiIHdpZHRoPSIxNTAiIGhlaWdodD0iNzYiLz4KICA8dGV4dCBjbGFzcz0ibGFiZWwiIHg9IjEzMiIgeT0iMTkyIj5TVEFSVDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic21hbGwiIHg9IjExNyIgeT0iMjE2Ij7liJ3lp4vnirbmgIE8L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJub2RlIiB4PSIzMDAiIHk9IjE1MCIgd2lkdGg9IjIyMCIgaGVpZ2h0PSI5NiIvPgogIDx0ZXh0IGNsYXNzPSJyb2xlIiB4PSIzMzAiIHk9IjE4MCI+Um91dGU8L3RleHQ+CiAgPHRleHQgY2xhc3M9ImxhYmVsIiB4PSIzNDMiIHk9IjIwNiI+cm91dGVfcmVxdWVzdDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic21hbGwiIHg9IjMzMCIgeT0iMjI5Ij7lhpnlhaUgcm91dGUgLyByZWFzb248L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJub2RlQWNjZW50IiB4PSI2MDAiIHk9IjE1MCIgd2lkdGg9IjIzMCIgaGVpZ2h0PSI5NiIvPgogIDx0ZXh0IGNsYXNzPSJyb2xlIiB4PSI2MzAiIHk9IjE4MCI+UmVhc29uPC90ZXh0PgogIDx0ZXh0IGNsYXNzPSJsYWJlbCIgeD0iNjUwIiB5PSIyMDYiPmFuYWx5emVfZ29hbDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic21hbGwiIHg9IjYyNiIgeT0iMjI5Ij7or4bliKvku7vliqHnsbvlnovlkozorqHliJI8L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJub2RlQWNjZW50IiB4PSI5MzAiIHk9IjE1MCIgd2lkdGg9IjI1MCIgaGVpZ2h0PSI5NiIvPgogIDx0ZXh0IGNsYXNzPSJyb2xlIiB4PSI5NjAiIHk9IjE4MCI+UGxhbjwvdGV4dD4KICA8dGV4dCBjbGFzcz0ibGFiZWwiIHg9Ijk2NCIgeT0iMjA2Ij5wbGFuX2Jyb3dzZXJfYWN0aW9uPC90ZXh0PgogIDx0ZXh0IGNsYXNzPSJzbWFsbCIgeD0iOTY3IiB5PSIyMjkiPueUn+aIkCBicm93c2VyIOaMh+S7pDwvdGV4dD4KCiAgPHJlY3QgY2xhc3M9Im5vZGVBY2NlbnQiIHg9IjkzMCIgeT0iMzMwIiB3aWR0aD0iMjUwIiBoZWlnaHQ9Ijk2Ii8+CiAgPHRleHQgY2xhc3M9InJvbGUiIHg9Ijk2MCIgeT0iMzYwIj5BY3Q8L3RleHQ+CiAgPHRleHQgY2xhc3M9ImxhYmVsIiB4PSIxMDA2IiB5PSIzODYiPmJyb3dzZXJfdXNlPC90ZXh0PgogIDx0ZXh0IGNsYXNzPSJzbWFsbCIgeD0iOTY1IiB5PSI0MDkiPuiwg+eUqCBicm93c2VyLXVzZSDmiafooYw8L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJub2RlQWNjZW50IiB4PSI2MDAiIHk9IjMzMCIgd2lkdGg9IjIzMCIgaGVpZ2h0PSI5NiIvPgogIDx0ZXh0IGNsYXNzPSJyb2xlIiB4PSI2MzAiIHk9IjM2MCI+T2JzZXJ2ZSAvIEV2YWx1YXRlPC90ZXh0PgogIDx0ZXh0IGNsYXNzPSJsYWJlbCIgeD0iNjQ1IiB5PSIzODYiPmV2YWx1YXRlX3Jlc3VsdDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic21hbGwiIHg9IjYzNSIgeT0iNDA5Ij7lpI3moLjmiafooYznu5Pmnpw8L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJub2RlV2FybiIgeD0iMzAwIiB5PSIzMzAiIHdpZHRoPSIyMjAiIGhlaWdodD0iOTYiLz4KICA8dGV4dCBjbGFzcz0icm9sZSIgeD0iMzMwIiB5PSIzNjAiIGZpbGw9IiNhODY3MDAiPlJlamVjdDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ibGFiZWwiIHg9IjM0MiIgeT0iMzg2Ij5yZWplY3RfcmVxdWVzdDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic21hbGwiIHg9IjMzMCIgeT0iNDA5Ij7or7fmsYLml6DmlYjml7bov5Tlm548L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJub2RlRW5kIiB4PSIzMDAiIHk9IjU0MCIgd2lkdGg9IjIyMCIgaGVpZ2h0PSI5NiIvPgogIDx0ZXh0IGNsYXNzPSJyb2xlIiB4PSIzMzAiIHk9IjU3MCI+UmVwb3J0PC90ZXh0PgogIDx0ZXh0IGNsYXNzPSJsYWJlbCIgeD0iMzU0IiB5PSI1OTYiPndyaXRlX3JlcG9ydDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic21hbGwiIHg9IjMzMyIgeT0iNjE5Ij7mnIDnu4jmiqXlkYrlh7rlj6M8L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJub2RlRW5kIiB4PSI2MDAiIHk9IjU1MCIgd2lkdGg9IjE1MCIgaGVpZ2h0PSI3NiIvPgogIDx0ZXh0IGNsYXNzPSJsYWJlbCIgeD0iNjU2IiB5PSI1ODIiPkVORDwvdGV4dD4KICA8dGV4dCBjbGFzcz0ic21hbGwiIHg9IjYzMiIgeT0iNjA2Ij7ov5Tlm54gQVBJPC90ZXh0PgoKICA8cGF0aCBjbGFzcz0iZWRnZSIgZD0iTTIzMCAxOTggSDMwMCIvPgogIDxwYXRoIGNsYXNzPSJlZGdlIiBkPSJNNTIwIDE5OCBINjAwIi8+CiAgPHBhdGggY2xhc3M9ImVkZ2UiIGQ9Ik04MzAgMTk4IEg5MzAiLz4KICA8cGF0aCBjbGFzcz0iZWRnZSIgZD0iTTEwNTUgMjQ2IFYzMzAiLz4KICA8cGF0aCBjbGFzcz0iZWRnZSIgZD0iTTkzMCAzNzggSDgzMCIvPgogIDxwYXRoIGNsYXNzPSJlZGdlIiBkPSJNNjAwIDM3OCBINTIwIi8+CiAgPHBhdGggY2xhc3M9InJlamVjdCIgZD0iTTQxMCAyNDYgVjMzMCIvPgogIDxwYXRoIGNsYXNzPSJyZWplY3QiIGQ9Ik00MTAgNDI2IFY1NDAiLz4KICA8cGF0aCBjbGFzcz0iZWRnZSIgZD0iTTcxNSA0MjYgQzcxNSA1MDAgNTQwIDUwOCA0MTAgNTQwIi8+CiAgPHBhdGggY2xhc3M9ImVkZ2UiIGQ9Ik01MjAgNTg4IEg2MDAiLz4KCiAgPHRleHQgY2xhc3M9InNtYWxsIiB4PSI1NDgiIHk9IjE4NCI+cm91dGU9YnJvd3Nlcl91c2U8L3RleHQ+CiAgPHRleHQgY2xhc3M9InNtYWxsIiB4PSI0MjQiIHk9IjI5MiIgZmlsbD0iI2E4NjcwMCI+cm91dGU9cmVqZWN0PC90ZXh0PgogIDx0ZXh0IGNsYXNzPSJzbWFsbCIgeD0iODM1IiB5PSIzNjIiPkJyb3dzZXJVc2VSZXN1bHQ8L3RleHQ+CiAgPHRleHQgY2xhc3M9InNtYWxsIiB4PSI1NDUiIHk9IjUwMCI+ZXZhbHVhdGlvbi9yZXBvcnQ8L3RleHQ+CgogIDxyZWN0IGNsYXNzPSJub3RlIiB4PSI4MCIgeT0iNjYwIiB3aWR0aD0iMTEwMCIgaGVpZ2h0PSI1NCIvPgogIDx0ZXh0IGNsYXNzPSJzbWFsbCIgeD0iMTA4IiB5PSI2OTIiPueKtuaAgea1gei9rOaguOW/g++8mnJlcXVlc3QgLT4gcm91dGUgLT4gdGFza190eXBlL3Rlc3RfcGxhbiAtPiBicm93c2VyX2luc3RydWN0aW9uIC0+IGJyb3dzZXJfdXNlX3Jlc3VsdCAtPiBldmFsdWF0aW9uL3JlcG9ydCAtPiBBUEkgcmVzcG9uc2U8L3RleHQ+Cjwvc3ZnPgo=)

```mermaid
stateDiagram-v2
    [*] --> route_request

    route_request --> analyze_goal: URL 和目标完整
    route_request --> reject_request: 缺少 URL 或目标

    analyze_goal --> plan_browser_action
    plan_browser_action --> browser_use
    browser_use --> evaluate_result
    evaluate_result --> write_report

    reject_request --> write_report
    write_report --> [*]
```

各节点职责如下：

| 节点                    | ReAct 角色         | 作用                          |
| --------------------- | ---------------- | --------------------------- |
| `route_request`       | Route            | 检查 URL 和测试目标是否完整            |
| `analyze_goal`        | Reason           | 判断任务类型，例如登录、导航、表单、通用页面行为    |
| `plan_browser_action` | Plan             | 生成面向 browser-use 的测试计划和执行指令 |
| `browser_use`         | Act              | 调用 browser-use 执行真实浏览器操作    |
| `evaluate_result`     | Observe/Evaluate | 根据执行结果做外层复核                 |
| `reject_request`      | Reject           | 请求不完整时拒绝执行                  |
| `write_report`        | Report           | 输出最终 Markdown 报告            |

这层 ReAct 的价值在于：报告不再只是“成功/失败”，而是能看到 Agent 是怎么理解任务、怎么计划执行、最后怎么判断结果的。

### route_request：入口路由节点

`route_request` 是整个状态机的入口节点。它不做页面操作，只做请求校验。

它关注两个字段：

```text
request.base_url
request.goal
```

如果 URL 或测试目标为空，就把状态写成：

```text
route = "reject"
route_reason = "缺少目标 URL 或自然语言测试目标。"
```

如果请求完整，就写成：

```text
route = "browser_use"
route_reason = "请求有效，交给 browser-use 执行。"
```

这个节点的意义是把“请求能不能执行”这件事前置，避免无效任务进入后面的分析和浏览器执行阶段。

### analyze_goal：任务分析节点

`analyze_goal` 是 Reason 节点。它会读取用户的自然语言目标，并判断任务类型。

当前内置了几类任务：

| 任务类型     | 触发关键词示例                 | 生成的测试计划方向               |
| -------- | ----------------------- | ----------------------- |
| 登录/认证测试  | 登录、登陆、login、sign in     | 找登录入口、输入凭证、提交、判断登录态     |
| 导航/跳转巡检  | 导航、顶部、跳转、链接、nav、menu    | 找导航区域、逐个点击、检查 URL 和页面内容 |
| 表单/输入测试  | 表单、提交、输入、搜索、form、search | 找输入区域、填写字段、提交、观察反馈      |
| 通用页面行为测试 | 其他目标                    | 根据页面结构和用户目标自由规划         |

这个节点会写入：

```text
task_type
test_plan
observations
```

比如用户输入：

```text
测试一下这个页面的登录功能
```

节点会生成：

```text
task_type = "登录/认证测试"

test_plan = [
  "打开目标页面并等待首屏加载完成。",
  "识别登录入口，必要时处理弹窗、菜单或跳转。",
  "根据用户提供的凭证填写账号和密码。",
  "提交登录表单并等待页面状态变化。",
  "观察登录后页面、头像、按钮、弹窗或 URL 变化，判断是否登录成功。"
]
```

### plan_browser_action：执行计划节点

`plan_browser_action` 是 Plan 节点。它不会打开浏览器，而是把前面分析出来的任务类型和测试计划，整理成一段更适合 browser-use 执行的指令。

这个节点会写入：

```text
browser_instruction
observations
```

`browser_instruction` 里包含：

```text
目标页面
任务类型
用户原始测试目标
外层 ReAct 测试计划
执行要求
输出约束
```

其中有一条很重要：

```text
必须遵守 browser-use 系统要求的 AgentOutput JSON 格式；
不要在 JSON 外输出普通文本。
```

这是为了减少模型直接输出中文总结导致 `AgentOutput Invalid JSON` 的概率。

### browser_use：浏览器执行节点

`browser_use` 是 Act 节点。它会把 `browser_instruction` 放回 `TestRequest.goal`，再交给 browser-use。

它负责写入：

```text
browser_use_result
report
observations
errors
```

browser-use 内部会完成更细的循环：

```text
观察页面
决定下一步动作
点击 / 输入 / 等待 / 跳转
再次观察
判断是否完成
```

外层 LangGraph 不需要知道每一个 DOM 操作细节，只需要拿回 browser-use 的执行历史和最终结果。

### evaluate_result：外层评估节点

`evaluate_result` 是 Observe/Evaluate 节点。它读取 `browser_use_result`，做一次保守复核。

当前规则是：

| browser-use 结果          | 外层评估      |
| ----------------------- | --------- |
| `success=True`          | 通过        |
| 有 `errors`              | 失败        |
| 有 `final_result` 但未明确成功 | 失败，需要人工复核 |
| 没有有效结果                  | 失败        |

这个节点会写入：

```text
evaluation
observations
report
```

它的作用不是替代 browser-use 判断，而是让外层报告里有一个稳定、可解释的最终复核结论。

### reject_request：拒绝节点

`reject_request` 是安全出口。当请求缺少 URL 或测试目标时，状态机会走到这里。

它会直接生成失败报告：

```text
# 测试请求已拒绝

缺少目标 URL 或自然语言测试目标。
```

这个节点保证无效请求不会进入模型调用和浏览器执行阶段。

### write_report：报告出口节点

`write_report` 是最终出口节点。它不再改变业务结果，只负责作为状态机的收口。

所有路径最终都会走到它：

```text
成功执行路径 -> write_report
拒绝执行路径 -> write_report
执行失败路径 -> write_report
```

## 路由设计

节点负责“干活”，路由负责“决定下一步去哪”。

当前条件路由函数很薄：

```python
def route_after_router(state: TestAgentState) -> Literal["browser_use", "reject"]:
    return state["route"]
```

它只读取 `route_request` 写入的 `state["route"]`。

对应的边定义是：

```python
graph.add_conditional_edges(
    "route_request",
    route_after_router,
    {
        "browser_use": "analyze_goal",
        "reject": "reject_request",
    },
)
```

也就是说：

```text
route = browser_use  -> analyze_goal
route = reject       -> reject_request
```

这里有一个小细节：路由名字叫 `browser_use`，但它并不是直接跳到 `browser_use` 节点，而是先跳到 `analyze_goal`。因为 `browser_use` 在这里表示“这是一个可执行的浏览器测试请求”，真正执行前还需要经过 Reason 和 Plan。

完整边定义可以理解成：

```text
START
  -> route_request
  -> 条件路由
      -> analyze_goal
      -> plan_browser_action
      -> browser_use
      -> evaluate_result
      -> write_report
      -> END

START
  -> route_request
  -> 条件路由
      -> reject_request
      -> write_report
      -> END
```

## 状态流转图

下面这张图更关注状态字段的变化，而不是节点名字。

```mermaid
flowchart TD
    A["初始状态<br/>request"] --> B["route_request<br/>写入 route / route_reason"]

    B -->|"route=browser_use"| C["analyze_goal<br/>写入 task_type / test_plan / observations"]
    C --> D["plan_browser_action<br/>写入 browser_instruction / observations"]
    D --> E["browser_use<br/>写入 browser_use_result / errors / observations"]
    E --> F["evaluate_result<br/>写入 evaluation / report / observations"]
    F --> G["write_report<br/>返回最终状态"]

    B -->|"route=reject"| H["reject_request<br/>写入 report / errors"]
    H --> G

    G --> I["API 响应<br/>success / route / title / markdown / artifacts"]
```

用表格展开就是：

| 阶段  | 输入字段                    | 输出字段                    | 说明             |
| --- | ----------------------- | ----------------------- | -------------- |
| 初始化 | 前端 payload              | `request`、空报告、空错误       | 服务层构造初始状态      |
| 路由  | `request`               | `route`、`route_reason`  | 判断是否可执行        |
| 分析  | `request.goal`          | `task_type`、`test_plan` | 识别任务类型         |
| 计划  | `task_type`、`test_plan` | `browser_instruction`   | 生成浏览器执行指令      |
| 执行  | `browser_instruction`   | `browser_use_result`    | 调用 browser-use |
| 评估  | `browser_use_result`    | `evaluation`、`report`   | 外层复核           |
| 输出  | `report`                | API response            | 前端展示           |

## 状态机装配

状态机装配代码集中在 `test_agent/graph/builder.py`。

简化后大概是：

```python
graph = StateGraph(TestAgentState)

graph.add_node("route_request", route_request)
graph.add_node("analyze_goal", analyze_goal)
graph.add_node("plan_browser_action", plan_browser_action)
graph.add_node("browser_use", run_browser_use_agent)
graph.add_node("evaluate_result", evaluate_result)
graph.add_node("reject_request", reject_request)
graph.add_node("write_report", write_report)

graph.add_edge(START, "route_request")

graph.add_conditional_edges(
    "route_request",
    route_after_router,
    {
        "browser_use": "analyze_goal",
        "reject": "reject_request",
    },
)

graph.add_edge("analyze_goal", "plan_browser_action")
graph.add_edge("plan_browser_action", "browser_use")
graph.add_edge("browser_use", "evaluate_result")
graph.add_edge("evaluate_result", "write_report")
graph.add_edge("reject_request", "write_report")
graph.add_edge("write_report", END)
```

这段代码就是整个 Agent 的骨架。后面如果要扩展能力，通常也是在这里加节点和边。

比如增加失败重试，可以变成：

```text
browser_use -> evaluate_result
evaluate_result -> retry_browser_use
evaluate_result -> write_report
```

增加人工确认，可以变成：

```text
analyze_goal -> plan_browser_action -> human_confirm -> browser_use
```

增加不同执行器，可以变成：

```text
route_request -> analyze_goal -> route_executor
route_executor -> browser_use
route_executor -> api_test
route_executor -> link_crawler
```

## 请求和响应

前端调用接口：

```http
POST /api/agent/run
```

请求示例：

```json
{
  "url": "https://www.example.com/",
  "instruction": "测试一下这个页面的登录功能，登录凭证：user@example.com、******",
  "headed": true,
  "timeout_ms": 15000,
  "max_links": 30,
  "include_cross_origin": false
}
```

响应示例：

```json
{
  "success": true,
  "route": "browser_use",
  "title": "browser-use 自动化测试报告",
  "markdown": "...",
  "artifacts": []
}
```

前端页面主要分两栏：

```text
左侧：输入 URL、测试目标、超时时间、是否打开浏览器
右侧：展示 Markdown 测试报告
```

有头模式下，可以直接看到浏览器被 Agent 操作：打开页面、点击按钮、输入账号、提交表单、等待页面变化。

## browser-use 执行封装

核心封装大概是这样：

```python
llm = ChatOpenAI(
    model=OPENAI_MODEL,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    temperature=0,
    dont_force_structured_output=not force_structured_output,
    add_schema_to_system_prompt=not force_structured_output,
)

profile = BrowserProfile(
    headless=not request.headed,
    downloads_path=Path(BROWSER_USE_DOWNLOADS_DIR),
    traces_dir=Path(BROWSER_USE_TRACES_DIR),
    user_data_dir=Path(BROWSER_USE_TRACES_DIR).parent / "user_data",
)

agent = Agent(
    task=_build_task(request),
    llm=llm,
    browser_profile=profile,
    use_vision=True,
    step_timeout=max(30, int(request.timeout_ms / 1000)),
    max_failures=3,
    source="langchain1-browser-use",
)

history = await agent.run(max_steps=40)
```

执行完成后，会把 browser-use 的历史对象整理成稳定的数据结构：

```python
class BrowserUseResult(BaseModel):
    success: bool = False
    final_result: str = ""
    errors: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    steps: int = 0
    duration_seconds: float | None = None
```

这样前端不需要理解 browser-use 内部对象，只需要渲染稳定的报告字段。

## 一个登录测试案例

测试目标：

```text
测试某页面的登录功能，使用测试账号完成登录。
```

Agent 的执行过程大致是：

```text
1. 打开目标页面
2. 点击页面右上角 Login 按钮
3. 等待登录弹窗出现
4. 输入邮箱
5. 输入密码
6. 点击登录按钮提交
7. 等待页面响应
8. 根据页面右上角状态变化判断是否登录成功
```

最终报告里会包含：

```text
测试结果：通过
任务类型：登录/认证测试
执行步数：7
耗时：约 80 秒

ReAct 测试计划：
1. 打开目标页面并等待首屏加载完成
2. 识别登录入口
3. 填写账号和密码
4. 提交登录表单
5. 观察登录后页面状态

ReAct 轨迹：
- Reason：识别任务类型为登录/认证测试
- Plan：已生成面向 browser-use 的浏览器执行指令
- Act：browser-use 执行完成
- Evaluate：外层评估为通过
```

这个案例说明系统不是简单打开网页，而是完成了一段真实、多步骤、有状态变化的浏览器测试。

## 踩坑一：模型不支持 image_url

browser-use 开启视觉模式后，会把页面截图发给模型。如果模型不支持图片输入，就会报：

```text
Model do not support image input
param: image_url
```

这个错误的意思是：当前模型只能处理文本，不能处理 browser-use 传过去的截图。

解决方式有两个：

```text
1. 换支持视觉输入的模型
2. 临时关闭 use_vision
```

我最终选择换支持视觉的模型，并保持：

```python
Agent(
    ...,
    use_vision=True,
)
```

原因是复杂页面里，视觉信息很重要。比如“右上角 Login 按钮”“弹窗里的提交按钮”“头像图标”这类目标，单靠 DOM 不一定稳定。

## 踩坑二：json_schema 不兼容

browser-use 每一步都要求模型返回结构化的 `AgentOutput` JSON。但有些 OpenAI 兼容接口不支持：

```text
response_format.type=json_schema
```

会报：

```text
response_format.type=json_schema is not supported by this model
```

早期我为了兼容这类模型，关闭了强制结构化输出：

```python
dont_force_structured_output=True
add_schema_to_system_prompt=True
```

这样可以避免接口报 400，但也带来了另一个问题。

## 踩坑三：AgentOutput Invalid JSON

关闭强制结构化输出后，模型有时会不按 JSON 返回，而是直接输出中文：

```text
API/Skills 跳转成功...
```

browser-use 期待的是 `AgentOutput` JSON，于是就会报：

```text
1 validation error for AgentOutput
Invalid JSON: expected value at line 1 column 1
```

这不是页面跳转失败，而是模型返回格式不符合 browser-use 要求。

最终我做了一个兼容策略：

```text
默认优先使用 json_schema 强制结构化输出。
如果模型明确报 json_schema 不支持，再自动降级到 prompt schema 模式。
同时在任务指令里强调：不要在 JSON 外输出中文、Markdown 或普通文本。
```

对应配置：

```python
BROWSER_USE_FORCE_STRUCTURED_OUTPUT = os.getenv("BROWSER_USE_FORCE_STRUCTURED_OUTPUT", "1") != "0"
```

调用时：

```python
ChatOpenAI(
    ...,
    dont_force_structured_output=not force_structured_output,
    add_schema_to_system_prompt=not force_structured_output,
)
```

降级判断：

```python
def _is_json_schema_unsupported(exc: Exception) -> bool:
    message = str(exc).lower()
    return "json_schema" in message and (
        "not support" in message
        or "not supported" in message
        or "invalidparameter" in message
        or "response_format" in message
    )
```

这比一直关闭结构化输出稳定很多。

## 踩坑四：browser-use 默认写用户目录

browser-use 默认可能会写入：

```text
C:\Users\<user>\.config\browseruse
```

在某些受限运行环境中，这个目录可能没有权限。

所以我把 browser-use 的目录统一迁移到项目内：

```text
artifacts/browser_use/config
artifacts/browser_use/profiles
artifacts/browser_use/downloads
artifacts/browser_use/traces
```

配置方式：

```python
os.environ.setdefault("BROWSER_USE_CONFIG_DIR", str(BROWSER_USE_CONFIG_DIR))
os.environ.setdefault("BROWSER_USE_PROFILES_DIR", str(BROWSER_USE_PROFILES_DIR))
os.environ.setdefault("BROWSER_USE_DOWNLOADS_DIR", str(BROWSER_USE_DOWNLOADS_DIR))
os.environ.setdefault("BROWSER_USE_TRACES_DIR", str(BROWSER_USE_TRACES_DIR))
```

这样项目部署和迁移时更可控，也避免污染用户目录。

## 为什么要做外层结果规整

browser-use 的原始历史对象很有信息量，但不适合直接给前端。

比如失败时可能出现：

```text
success = None
errors = [None]
```

如果直接塞进 Pydantic 模型，会出现校验错误。

所以需要做规整：

```python
raw_errors = _safe_call(history, "errors", default=[]) or []
errors = [str(error) for error in raw_errors if error is not None]

raw_success = _safe_call(history, "is_successful", default=None)
success = bool(raw_success) if raw_success is not None else not bool(errors)
```

规整之后，前端永远拿到稳定结构：

```text
success
final_result
errors
urls
screenshots
steps
duration_seconds
```

这一步很重要。Agent 系统里，模型和浏览器都可能出现不稳定结果，前端接口必须尽量稳定。

## 当前项目结构

核心文件：

```text
test_agent/
  agent_service.py        # 前端调用的服务层
  web_app.py              # FastAPI + 内置前端页面
  browser_use_runner.py   # browser-use 执行封装
  models.py               # 请求、结果、状态协议
  settings.py             # API Key、browser-use 工作目录等配置
  graph/
    builder.py            # LangGraph 状态机装配
    nodes.py              # ReAct 节点实现
    routing.py            # 条件边路由

run_web_app.py            # 启动 FastAPI 服务
requirements.txt          # Python 依赖
```

核心依赖：

```text
browser-use
langgraph
fastapi
uvicorn
pydantic
python-dotenv
playwright
```

## 当前效果

目前这个初版已经做到：

- 前端输入自然语言测试目标
- 后端 API 接收任务
- LangGraph 外层 ReAct 编排
- browser-use 驱动真实浏览器
- 支持有头模式查看操作过程
- 支持视觉模型理解页面截图
- 输出中文 Markdown 测试报告
- 报告中包含测试计划、执行轨迹、最终结果和错误信息

它还不是一个完整测试平台，但已经有了可扩展的骨架。

## 后续可以怎么扩展

后面可以继续做这些增强：

| 方向   | 说明                                   |
| ---- | ------------------------------------ |
| 测试历史 | 保存每次执行的 URL、目标、报告、截图和耗时              |
| 报告管理 | 在前端提供历史报告列表和详情页                      |
| 账号管理 | 把测试账号从自然语言中拆出来，改成安全凭证配置              |
| 失败重试 | 对网络抖动、元素加载慢、模型偶发格式错误做自动重试            |
| 截图归档 | 将 browser-use 截图统一复制到项目 artifacts 目录 |
| 断言增强 | 允许用户配置必须出现的文本、URL 变化或页面状态            |
| 巡检模式 | 针对导航栏、按钮、链接做批量跳转检查                   |
| 多浏览器 | 支持 Chromium、Chrome、Edge 等不同浏览器配置     |
| 多环境  | 支持测试环境、预发环境、生产环境 URL 切换              |

我觉得最值得优先做的是“测试历史”和“失败重试”。

测试历史能让这个工具从一次性 Demo 变成可追踪系统；失败重试则能显著提升 AI 自动化测试的稳定性。

## 总结

这次实践最大的感受是：AI 自动化测试的难点不只是“让浏览器动起来”，而是让系统在复杂页面里持续完成这几件事：

```text
理解目标
观察页面
规划动作
执行操作
判断结果
解释失败
```

Playwright 解决的是浏览器执行问题，browser-use 解决了一部分页面理解和多步操作问题，LangGraph 则适合做外层流程编排和可解释状态机。

最终组合起来，就是：

```text
LangGraph 负责测试流程
browser-use 负责浏览器操作
FastAPI 负责前端接入
Markdown 报告负责结果表达
```

这个初版已经可以完成真实页面的登录测试，也能把执行过程整理成中文报告。它离完整测试平台还有距离，但已经证明了一件事：自然语言驱动的浏览器自动化测试，是可以落到一个可运行工程里的。
