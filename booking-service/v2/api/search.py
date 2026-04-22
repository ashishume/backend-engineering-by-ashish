import json
import os
from typing import Any, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class TrieNode:
    def __init__(self):
        self.children = {}  # char -> TrieNode
        self.indices = []   # references to data list indices
        self.is_end = False


data: list[dict[str, Any]] = []
root = TrieNode()

MAX_PER_NODE = 200
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "business.json")


def reset_index() -> None:
    global root
    root = TrieNode()
    data.clear()


def insert(word: str, idx: int) -> None:
    node = root
    for ch in word:
        if ch not in node.children:
            node.children[ch] = TrieNode()
        node = node.children[ch]

        if len(node.indices) < MAX_PER_NODE:
            node.indices.append(idx)

    node.is_end = True


def build_trie(file_path: str) -> None:
    reset_index()
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            obj = json.loads(line)
            data.append(obj)

            name = obj.get("name", "")
            if isinstance(name, str) and name.strip():
                # Use actual in-memory index, not file line number
                insert(name.lower().strip(), len(data) - 1)


@router.on_event("startup")
def startup() -> None:
    build_trie(FILE_PATH)


class SearchPayload(BaseModel):
    name: Optional[str] = None
    page: int = 1
    per_page: int = DEFAULT_PER_PAGE


def _paginate(items: list[dict[str, Any]], page: int, per_page: int) -> dict[str, Any]:
    page = max(page, 1)
    per_page = max(1, min(per_page, MAX_PER_PAGE))

    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page

    return {
        "items": items[start:end],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    }


def search_prefix(prefix: str) -> list[dict[str, Any]]:
    node = root

    for ch in prefix:
        if ch not in node.children:
            return []
        node = node.children[ch]

    return [data[i] for i in node.indices if 0 <= i < len(data)]


@router.post("/")
def search_business(payload: SearchPayload):
    results = data

    if payload.name:
        prefix = payload.name.lower().strip()
        if prefix:
            results = search_prefix(prefix)

    paginated = _paginate(results, payload.page, payload.per_page)
    return {
        "results": paginated["items"],
        "pagination": paginated["pagination"],
    }


@router.get("/")
def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
):
    q = q.lower().strip()
    results = search_prefix(q)

    slim_results = [{"name": r.get("name"), "city": r.get("city")} for r in results]
    paginated = _paginate(slim_results, page, per_page)

    return {
        "results": paginated["items"],
        "pagination": paginated["pagination"],
    }