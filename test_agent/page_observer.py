"""测试计划前的页面结构快照。"""

from __future__ import annotations

from datetime import datetime

from playwright.sync_api import sync_playwright

from test_agent.models import PageSnapshot, PageSnapshotElement, TestRequest
from test_agent.settings import PAGE_OBSERVATION_DIR


def capture_page_snapshot(request: TestRequest, task_type: str) -> PageSnapshot:
    """打开页面，截图并提取计划阶段可用的结构化页面快照。"""

    PAGE_OBSERVATION_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    screenshot_path = PAGE_OBSERVATION_DIR / f"snapshot_{timestamp}.png"

    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright)
            page = browser.new_page(viewport={"width": 1440, "height": 1200})
            page.goto(request.base_url, wait_until="domcontentloaded", timeout=request.timeout_ms)
            page.wait_for_timeout(1200)

            page.screenshot(path=str(screenshot_path), full_page=False)
            title = page.title()
            current_url = page.url
            raw_snapshot = _extract_snapshot(page)
            browser.close()

        elements = [
            PageSnapshotElement(**item)
            for item in raw_snapshot["interactive_elements"][: request.max_candidates]
        ]
        links = _format_links([item for item in elements if item.tag == "a"])
        footer_links = _format_links([item for item in elements if item.tag == "a" and item.section == "footer"])

        candidate_links = links[: request.max_links]
        summary = _build_summary(
            title=title,
            current_url=current_url,
            viewport=raw_snapshot["viewport"],
            scroll=raw_snapshot["scroll"],
            visible_text=raw_snapshot["visible_text"],
            elements=elements,
            links=links,
            footer_links=footer_links,
            candidate_links=candidate_links,
        )
        return PageSnapshot(
            success=True,
            url=current_url,
            title=title,
            screenshot=str(screenshot_path),
            summary=summary,
            viewport=raw_snapshot["viewport"],
            scroll=raw_snapshot["scroll"],
            visible_text=raw_snapshot["visible_text"][:80],
            links=links[: request.max_links],
            footer_links=footer_links[: request.max_links],
            interactive_elements=elements[: request.max_candidates],
        )
    except Exception as exc:
        return PageSnapshot(
            success=False,
            url=request.base_url,
            screenshot=str(screenshot_path) if screenshot_path.exists() else "",
            error=str(exc),
            summary=f"页面快照生成失败：{exc}",
        )


def observe_page_before_plan(request: TestRequest, task_type: str) -> PageSnapshot:
    """兼容旧调用名。"""

    return capture_page_snapshot(request, task_type)


def _extract_snapshot(page) -> dict:
    return page.evaluate(
        """
        () => {
          const viewport = { width: window.innerWidth, height: window.innerHeight };
          const pageHeight = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
          const scroll = {
            x: window.scrollX,
            y: window.scrollY,
            pageHeight,
            viewportBottom: window.scrollY + window.innerHeight
          };

          const visibleText = Array.from(document.querySelectorAll('h1,h2,h3,h4,p,li,button,a,label'))
            .map((element) => (element.innerText || element.textContent || '').trim().replace(/\\s+/g, ' '))
            .filter(Boolean)
            .filter((text, index, array) => array.indexOf(text) === index)
            .slice(0, 120);

          const sectionOf = (element) => {
            if (element.closest('footer')) return 'footer';
            if (element.closest('header')) return 'header';
            if (element.closest('nav')) return 'nav';
            if (element.closest('main')) return 'main';
            const rect = element.getBoundingClientRect();
            const absoluteTop = rect.top + window.scrollY;
            if (absoluteTop < window.innerHeight * 0.45) return 'header_like';
            if (absoluteTop > pageHeight * 0.80) return 'bottom';
            if (absoluteTop > pageHeight * 0.60) return 'footer_like';
            return 'main';
          };

          const roleOf = (element) => {
            const explicit = element.getAttribute('role');
            if (explicit) return explicit;
            const tag = element.tagName.toLowerCase();
            if (tag === 'a') return 'link';
            if (tag === 'button') return 'button';
            if (tag === 'input') return 'textbox';
            if (tag === 'select') return 'combobox';
            if (tag === 'textarea') return 'textbox';
            return '';
          };

          const interactiveElements = Array.from(document.querySelectorAll('a,button,input,textarea,select,[role="button"],[role="link"]'))
            .map((element) => {
              const rect = element.getBoundingClientRect();
              const style = window.getComputedStyle(element);
              const visible = rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              const tag = element.tagName.toLowerCase();
              const text = (element.innerText || element.value || element.textContent || '').trim().replace(/\\s+/g, ' ');
              return {
                tag,
                role: roleOf(element),
                section: sectionOf(element),
                text,
                href: element.href || element.getAttribute('href') || '',
                aria_label: element.getAttribute('aria-label') || '',
                placeholder: element.getAttribute('placeholder') || '',
                input_type: element.getAttribute('type') || '',
                visible,
                bbox: {
                  x: Number(rect.x.toFixed(1)),
                  y: Number(rect.y.toFixed(1)),
                  width: Number(rect.width.toFixed(1)),
                  height: Number(rect.height.toFixed(1))
                }
              };
            })
            .filter((item) => item.visible && (item.text || item.href || item.aria_label || item.placeholder));

          return { viewport, scroll, visible_text: visibleText, interactive_elements: interactiveElements };
        }
        """
    )


def _launch_browser(playwright):
    launch_attempts = [
        lambda: playwright.chromium.launch(headless=True),
        lambda: playwright.chromium.launch(channel="chrome", headless=True),
        lambda: playwright.chromium.launch(channel="msedge", headless=True),
    ]
    last_error: Exception | None = None
    for launch in launch_attempts:
        try:
            return launch()
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"无法启动页面快照浏览器：{last_error}")


def _format_links(elements: list[PageSnapshotElement]) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for element in elements:
        text = element.text or element.aria_label or "(无文本)"
        href = element.href or ""
        item = f"[{element.section}] {text} -> {href}"
        if item not in seen:
            seen.add(item)
            links.append(item)
    return links


def _build_summary(
    title: str,
    current_url: str,
    viewport: dict,
    scroll: dict,
    visible_text: list[str],
    elements: list[PageSnapshotElement],
    links: list[str],
    footer_links: list[str],
    candidate_links: list[str],
) -> str:
    buttons = [item for item in elements if item.role == "button" or item.tag == "button"]
    inputs = [item for item in elements if item.tag in {"input", "textarea", "select"}]
    lines = [
        f"页面标题：{title or '(无标题)'}",
        f"当前 URL：{current_url}",
        f"视口：{viewport.get('width')}x{viewport.get('height')}，滚动位置：{scroll.get('y')} / 页面高度：{scroll.get('pageHeight')}",
        f"可交互元素数：{len(elements)}，链接数：{len(links)}，按钮数：{len(buttons)}，输入控件数：{len(inputs)}",
    ]
    if visible_text:
        lines.append("页面可见文本摘要：")
        lines.extend(f"- {item}" for item in visible_text[:25])
    if buttons:
        lines.append("按钮/可点击控件摘要：")
        lines.extend(
            f"- [{item.section}] {item.text or item.aria_label or item.placeholder or item.tag}"
            for item in buttons[:25]
        )
    if inputs:
        lines.append("输入控件摘要：")
        lines.extend(
            f"- [{item.section}] {item.input_type or item.tag} {item.placeholder or item.aria_label or item.text}"
            for item in inputs[:20]
        )
    if candidate_links:
        lines.append("页面候选链接摘要：")
        lines.extend(f"- {item}" for item in candidate_links[:40])
    return "\n".join(lines)
