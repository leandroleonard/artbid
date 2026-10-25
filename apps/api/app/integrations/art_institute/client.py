from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import AppError, ErrorCode, not_found, validation

logger = logging.getLogger(__name__)

ARTWORK_ID_RE = re.compile(r"^aic_(\d{1,10})$")
SOURCE_LABEL = "Art Institute of Chicago"
DEFAULT_IMAGE = "/images/art-hero.jpg"
TAG_RE = re.compile(r"<[^>]+>")


class ArtworkNotFound(AppError):
    def __init__(self) -> None:
        super().__init__(404, ErrorCode.NOT_FOUND, "A obra não foi encontrada no catálogo.")


@dataclass
class Artwork:
    id: str
    title: str
    artist: str
    date: str
    description: str | None
    image_url: str
    image_alt: str
    source: str = SOURCE_LABEL

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "date": self.date,
            "description": self.description,
            "imageUrl": self.image_url,
            "imageAlt": self.image_alt,
            "source": self.source,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "externalId": self.id,
            "title": self.title,
            "artist": self.artist,
            "date": self.date,
            "description": self.description,
            "imageUrl": self.image_url,
            "imageAlt": self.image_alt,
            "source": self.source,
        }


def parse_artwork_id(value: str) -> int:
    match = ARTWORK_ID_RE.match((value or "").strip())
    if not match:
        raise validation(
            "Identificador de obra inválido.",
            {"artworkId": ["Formato esperado: aic_<numero>."]},
        )
    return int(match.group(1))


def strip_html(value: str | None, limit: int = 1200) -> str | None:
    if not value:
        return None
    text = TAG_RE.sub(" ", value)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    return text[:limit]


def iiif_image_url(image_id: str | None, config: dict[str, Any] | None) -> str:
    base = (config or {}).get("iiif_url") or "https://www.artic.edu/iiif/2"
    if not image_id:
        return DEFAULT_IMAGE
    if not re.match(r"^[A-Za-z0-9\-_/.]{1,120}$", image_id):
        return DEFAULT_IMAGE
    return f"{base.rstrip('/')}/{image_id}/full/843,/0/default.jpg"


def normalize_artwork(raw: dict[str, Any], config: dict[str, Any] | None = None) -> Artwork:
    try:
        artwork_id = int(raw["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(502, ErrorCode.UPSTREAM_INVALID_RESPONSE) from exc

    title = (raw.get("title") or "").strip() or "Sem título"
    artist = (
        raw.get("artist_title")
        or raw.get("artist_display")
        or raw.get("department_title")
        or "Artista desconhecido"
    )
    artist = re.sub(r"\s+", " ", str(artist)).strip()[:160]
    date_value = (raw.get("date_display") or raw.get("date_qualified") or "").strip()
    description = strip_html(raw.get("description")) or strip_html(raw.get("short_description"))
    image_url = iiif_image_url(raw.get("image_id"), config)
    alt = strip_html(raw.get("thumbnail", {}).get("alt_text") if isinstance(raw.get("thumbnail"), dict) else None, 200)
    return Artwork(
        id=f"aic_{artwork_id}",
        title=str(title)[:160],
        artist=artist,
        date=str(date_value)[:120],
        description=description,
        image_url=image_url,
        image_alt=alt or f"{title} — {artist}",
    )


class ArtInstituteClient:
    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.aic_base_url).rstrip("/")
        self._transport = transport

    BROWSER_UA = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 ArtBid/1.0 (+{contact})"
    )

    def _client(self) -> httpx.Client:
        timeout = httpx.Timeout(
            settings.aic_timeout_read_seconds, connect=settings.aic_timeout_connect_seconds
        )
        contact = settings.aic_contact_email or "leandroventur19@gmail.com"
        return httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=self._transport,
            headers={
                "Accept": "application/json",
                "User-Agent": self.BROWSER_UA.format(contact=contact),
                "AIC-User-Agent": f"ArtBid/1.0 ({contact})",
            },
            follow_redirects=False,
        )

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return self._attempt(path, params)
        except AppError as exc:
            if exc.status_code not in (502, 503, 504):
                raise
            logger.info(
                "aic_retry",
                extra={"extra_fields": {"path": path, "code": exc.code}},
            )
            return self._attempt(path, params)

    def _attempt(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            with self._client() as client:
                with client.stream("GET", path, params=params) as response:
                    if response.status_code == 404:
                        raise ArtworkNotFound()
                    if response.status_code >= 500:
                        raise AppError(503, ErrorCode.UPSTREAM_UNAVAILABLE)
                    if response.status_code in (401, 403, 429):
                        raise AppError(503, ErrorCode.UPSTREAM_UNAVAILABLE)
                    if response.status_code >= 400:
                        raise AppError(502, ErrorCode.UPSTREAM_INVALID_RESPONSE)
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > settings.aic_max_response_bytes:
                            raise AppError(502, ErrorCode.UPSTREAM_INVALID_RESPONSE)
                    try:
                        payload = httpx.Response(200, content=bytes(body)).json()
                    except ValueError as exc:
                        raise AppError(502, ErrorCode.UPSTREAM_INVALID_RESPONSE) from exc
        except httpx.TimeoutException as exc:
            logger.warning("aic_timeout", extra={"extra_fields": {"path": path}})
            raise AppError(504, ErrorCode.UPSTREAM_TIMEOUT) from exc
        except httpx.HTTPError as exc:
            logger.warning(
                "aic_transport_error",
                extra={"extra_fields": {"path": path, "error": type(exc).__name__}},
            )
            raise AppError(503, ErrorCode.UPSTREAM_UNAVAILABLE) from exc
        if not isinstance(payload, dict):
            raise AppError(502, ErrorCode.UPSTREAM_INVALID_RESPONSE)
        return payload

    def search(self, query: str, page: int = 1, page_size: int = 12) -> tuple[list[Artwork], int]:
        query = (query or "").strip()
        if len(query) < 2 or len(query) > 100:
            raise validation(
                "A pesquisa deve ter entre 2 e 100 caracteres.", {"q": ["Comprimento inválido."]}
            )
        page = max(1, page)
        page_size = max(1, min(page_size, settings.aic_page_size_max))
        payload = self._request(
            "/artworks/search",
            {
                "q": query,
                "page": page,
                "limit": page_size,
                "fields": "id,title,artist_title,artist_display,date_display,description,"
                "short_description,image_id,thumbnail,department_title",
            },
        )
        data = payload.get("data")
        if not isinstance(data, list):
            raise AppError(502, ErrorCode.UPSTREAM_INVALID_RESPONSE)
        config = payload.get("config") if isinstance(payload.get("config"), dict) else None
        artworks = [normalize_artwork(item, config) for item in data if isinstance(item, dict)]
        pagination = payload.get("pagination") or {}
        total = pagination.get("total") if isinstance(pagination, dict) else 0
        try:
            total_items = int(total or 0)
        except (TypeError, ValueError):
            total_items = 0
        if total_items < len(artworks):
            total_items = len(artworks)
        return artworks, total_items

    DETAIL_FIELDS = (
        "id,title,artist_title,artist_display,date_display,description,"
        "short_description,image_id,thumbnail,department_title"
    )

    def get(self, artwork_id: str) -> Artwork:
        numeric = parse_artwork_id(artwork_id)
        payload = self._request(f"/artworks/{numeric}", {"fields": self.DETAIL_FIELDS})
        data = payload.get("data")
        if not isinstance(data, dict):
            raise AppError(502, ErrorCode.UPSTREAM_INVALID_RESPONSE)
        config = payload.get("config") if isinstance(payload.get("config"), dict) else None
        artwork = normalize_artwork(data, config)
        if artwork.id != f"aic_{numeric}":
            raise AppError(502, ErrorCode.UPSTREAM_INVALID_RESPONSE)
        return artwork


_client_singleton: ArtInstituteClient | None = None


def get_aic_client() -> ArtInstituteClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = ArtInstituteClient()
    return _client_singleton


def reset_client() -> None:
    global _client_singleton
    _client_singleton = None


def artwork_not_found() -> AppError:
    return not_found("A obra não foi encontrada no catálogo.")
