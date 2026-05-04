from __future__ import annotations

from typing import Any


def page_title(page: dict[str, Any]) -> str:
    """Extract a useful title from a Notion page object."""

    properties = page.get("properties") or {}
    for value in properties.values():
        if value.get("type") != "title":
            continue
        text = _rich_text(value.get("title") or [])
        if text:
            return text
    return "Untitled Notion page"


def blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    """Convert supported Notion blocks into compact markdown-like text."""

    lines: list[str] = []
    for block in blocks:
        lines.extend(_block_lines(block, depth=0))
    return "\n".join(line for line in lines if line.strip()).strip()


def _block_lines(block: dict[str, Any], *, depth: int) -> list[str]:
    block_type = block.get("type", "")
    data = block.get(block_type) or {}
    indent = "  " * depth
    lines: list[str] = []

    if block_type == "paragraph":
        lines.extend(_plain_block_lines(data, indent))
    elif block_type == "heading_1":
        lines.append(f"# {_rich_text(data.get('rich_text') or [])}")
    elif block_type == "heading_2":
        lines.append(f"## {_rich_text(data.get('rich_text') or [])}")
    elif block_type == "heading_3":
        lines.append(f"### {_rich_text(data.get('rich_text') or [])}")
    elif block_type == "bulleted_list_item":
        lines.append(f"{indent}- {_rich_text(data.get('rich_text') or [])}")
    elif block_type == "numbered_list_item":
        lines.append(f"{indent}1. {_rich_text(data.get('rich_text') or [])}")
    elif block_type == "to_do":
        checked = "x" if data.get("checked") else " "
        lines.append(f"{indent}- [{checked}] {_rich_text(data.get('rich_text') or [])}")
    elif block_type == "toggle":
        lines.append(f"{indent}- {_rich_text(data.get('rich_text') or [])}")
    elif block_type == "quote":
        text = _rich_text(data.get("rich_text") or [])
        if text:
            lines.append(f"> {text}")
    elif block_type == "code":
        language = data.get("language") or ""
        text = _rich_text(data.get("rich_text") or [])
        lines.append(f"```{language}\n{text}\n```")
    elif block_type == "callout":
        text = _rich_text(data.get("rich_text") or [])
        if text:
            lines.append(f"{indent}> {text}")
    elif block_type == "child_page":
        title = data.get("title") or "Child page"
        lines.append(f"{indent}## {title}")
    elif block_type == "child_database":
        title = data.get("title") or "Child database"
        lines.append(f"{indent}## {title}")
    elif block_type == "bookmark":
        caption = _rich_text(data.get("caption") or [])
        url = data.get("url") or ""
        lines.append(f"{indent}- {caption or url}")
    elif block_type in {"image", "video", "file", "pdf", "audio", "embed", "link_preview"}:
        caption = _rich_text(data.get("caption") or [])
        url = _file_url(data)
        label = caption or url
        if label:
            lines.append(f"{indent}- {block_type}: {label}")
    elif block_type == "divider":
        lines.append("---")
    elif block_type == "table_row":
        cells = [" ".join(_rich_text(cell).split()) for cell in data.get("cells") or []]
        if cells:
            lines.append("| " + " | ".join(cells) + " |")

    for child in block.get("children") or []:
        lines.extend(_block_lines(child, depth=depth + 1))

    return [line for line in lines if line.strip()]


def _plain_block_lines(data: dict[str, Any], indent: str) -> list[str]:
    text = _rich_text(data.get("rich_text") or [])
    return [f"{indent}{text}"] if text else []


def _rich_text(items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in items:
        plain = item.get("plain_text")
        if plain:
            parts.append(plain)
            continue
        text = item.get("text") or {}
        content = text.get("content")
        if content:
            parts.append(content)
    return "".join(parts).strip()


def _file_url(data: dict[str, Any]) -> str:
    file_type = data.get("type")
    if file_type and isinstance(data.get(file_type), dict):
        return str(data[file_type].get("url") or "")
    return str(data.get("url") or "")
