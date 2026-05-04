from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings


class NotionClient:
    """Small REST client for the Notion endpoints needed by the memory index."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.notion_api_key)

    def search_shared_pages(self) -> list[dict[str, Any]]:
        """Return pages shared with the integration, capped by NOTION_MAX_PAGES."""

        self._require_api_key()
        pages: list[dict[str, Any]] = []
        cursor: str | None = None

        with self._client() as client:
            while len(pages) < self.settings.notion_max_pages:
                body: dict[str, Any] = {
                    "filter": {"property": "object", "value": "page"},
                    "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                    "page_size": min(100, self.settings.notion_max_pages - len(pages)),
                }
                if cursor:
                    body["start_cursor"] = cursor

                response = client.post("/v1/search", json=body)
                self._raise_for_status(response)
                payload = response.json()
                pages.extend(payload.get("results", []))
                if not payload.get("has_more"):
                    break
                cursor = payload.get("next_cursor")
                if not cursor:
                    break

        return pages[: self.settings.notion_max_pages]

    def fetch_block_tree(self, block_id: str, *, max_depth: int = 8) -> list[dict[str, Any]]:
        """Read all child blocks below a page/block recursively."""

        self._require_api_key()
        with self._client() as client:
            return self._fetch_children(client, block_id, depth=0, max_depth=max_depth)

    def _fetch_children(
        self,
        client: httpx.Client,
        block_id: str,
        *,
        depth: int,
        max_depth: int,
    ) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor

            response = client.get(f"/v1/blocks/{block_id}/children", params=params)
            self._raise_for_status(response)
            payload = response.json()
            for block in payload.get("results", []):
                if block.get("has_children") and depth < max_depth:
                    block["children"] = self._fetch_children(
                        client,
                        block["id"],
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                blocks.append(block)

            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
            if not cursor:
                break

        return blocks

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url="https://api.notion.com",
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.settings.notion_api_key}",
                "Notion-Version": self.settings.notion_version,
                "Content-Type": "application/json",
            },
        )

    def _require_api_key(self) -> None:
        if not self.configured:
            raise ValueError("NOTION_API_KEY is required to sync Notion memory")

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                payload = response.json()
                code = payload.get("code")
                message = payload.get("message")
                if code or message:
                    raise ValueError(
                        f"Notion API {response.status_code} {code}: {message}"
                    ) from exc
            except ValueError:
                raise
            except Exception:
                pass
            raise ValueError(
                f"Notion API {response.status_code}: {response.text}"
            ) from exc
