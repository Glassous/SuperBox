from functools import lru_cache

from app.catalog import TOOLS
from app.skill_spec import (
    AI_GUIDANCE,
    CONVENTIONS,
    ERROR_CONTRACT,
    ERROR_EXAMPLES,
    PUBLIC_ENDPOINTS,
    SKILL_DESCRIPTION,
    SKILL_VERSION,
    TOOL_ENDPOINTS,
    Endpoint,
)


def _render_endpoint(lines: list[str], endpoint: Endpoint, base: str, level: int) -> None:
    lines.append(f"{'#' * level} {endpoint['name']}")
    lines.append("")
    lines.append(f"`{endpoint['method']} {base}/api/v1{endpoint['path']}`")
    lines.append("")
    lines.append(endpoint["summary"])
    lines.append("")
    lines.append(f"请求：{endpoint['request']}")
    lines.append("")
    request_example = endpoint.get("request_example")
    if request_example:
        lines.append("请求示例：")
        lines.append("")
        lines.append(f"```{endpoint.get('request_language', 'json')}")
        lines.append(request_example.replace("$BASE", base))
        lines.append("```")
        lines.append("")
    lines.append(f"{endpoint.get('response_label', '成功响应示例')}：")
    lines.append("")
    lines.append(f"```{endpoint.get('response_language', 'json')}")
    lines.append(endpoint["response_example"])
    lines.append("```")
    lines.append("")


@lru_cache(maxsize=64)
def build_skill_markdown(base_url: str) -> str:
    base = base_url.rstrip("/")
    lines: list[str] = [
        "# Superbox API 官方 Skill",
        "",
        SKILL_DESCRIPTION,
        "",
        f"- 基础地址：{base}/api/v1",
        f"- OpenAPI 定义：{base}/api/v1/openapi.json",
        f"- 交互式文档：{base}/docs",
        "",
        "## 使用约定",
        "",
        *[f"- {convention}" for convention in CONVENTIONS],
        "",
        "## 全部功能列表",
        "",
        "### 公共接口",
        "",
    ]
    for endpoint in PUBLIC_ENDPOINTS:
        _render_endpoint(lines, endpoint, base, 4)
    for tool in TOOLS:
        endpoints = TOOL_ENDPOINTS.get(tool["slug"])
        if not endpoints:
            continue
        lines.append(f"### {tool['name']}（{tool['category']}）")
        lines.append("")
        lines.append(tool["description"])
        lines.append("")
        for endpoint in endpoints:
            _render_endpoint(lines, endpoint, base, 4)
    lines.extend(["## 错误契约", "", "失败响应为统一 JSON 结构，`details` 仅在字段校验失败时出现：", ""])
    for example in ERROR_EXAMPLES:
        lines.append("```json")
        lines.append(example)
        lines.append("```")
        lines.append("")
    lines.append("| HTTP 状态 | code | 含义 |")
    lines.append("| --- | --- | --- |")
    for entry in ERROR_CONTRACT:
        lines.append(f"| {entry['status']} | `{entry['code']}` | {entry['meaning']} |")
    lines.extend(["", "## 给 AI 平台的接入建议", ""])
    for item in AI_GUIDANCE:
        lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def _manifest_endpoint(
    endpoint: Endpoint, base: str, category: str, tool_slug: str | None = None
) -> dict:
    request_example = endpoint.get("request_example")
    return {
        "category": category,
        "tool": tool_slug,
        "method": endpoint["method"],
        "path": endpoint["path"],
        "url": f"{base}/api/v1{endpoint['path']}",
        "name": endpoint["name"],
        "summary": endpoint["summary"],
        "request": endpoint["request"],
        "request_format": endpoint.get("request_format", "json"),
        "request_example": request_example,
        "request_example_language": endpoint.get("request_language", "json")
        if request_example
        else None,
        "response_example": endpoint["response_example"],
        "response_example_language": endpoint.get("response_language", "json"),
    }


def build_skill_manifest(base_url: str) -> dict:
    base = base_url.rstrip("/")
    endpoints = [
        _manifest_endpoint(endpoint, base, "公共接口") for endpoint in PUBLIC_ENDPOINTS
    ]
    for tool in TOOLS:
        endpoints.extend(
            _manifest_endpoint(endpoint, base, tool["category"], tool["slug"])
            for endpoint in TOOL_ENDPOINTS.get(tool["slug"], [])
        )
    return {
        "name": "Superbox API 官方 Skill",
        "version": SKILL_VERSION,
        "base_url": f"{base}/api/v1",
        "description": SKILL_DESCRIPTION,
        "auth": "none",
        "endpoints_total": len(endpoints),
        "links": {
            "markdown_skill": f"{base}/api/v1/skill",
            "openapi": f"{base}/api/v1/openapi.json",
            "docs": f"{base}/docs",
        },
        "conventions": CONVENTIONS,
        "tools": [
            {
                "slug": tool["slug"],
                "name": tool["name"],
                "category": tool["category"],
                "description": tool["description"],
            }
            for tool in TOOLS
        ],
        "endpoints": endpoints,
        "errors": ERROR_CONTRACT,
        "error_examples": ERROR_EXAMPLES,
        "guidance": AI_GUIDANCE,
    }
