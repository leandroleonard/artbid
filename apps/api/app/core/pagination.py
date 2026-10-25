from __future__ import annotations

import math
from typing import Any, Generic, Sequence, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 50


class Pagination(BaseModel):
    page: int = Field(ge=1)
    pageSize: int = Field(ge=1, le=MAX_PAGE_SIZE)
    totalItems: int = Field(ge=0)
    totalPages: int = Field(ge=0)


def paginate(items: Sequence[T], page: int, page_size: int, total_items: int) -> dict[str, Any]:
    return {
        "data": list(items),
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total_items,
            "totalPages": math.ceil(total_items / page_size) if page_size else 0,
        },
    }


def data_envelope(data: Any) -> dict[str, Any]:
    return {"data": data}


class Page(BaseModel, Generic[T]):
    data: list[T]
    pagination: Pagination
