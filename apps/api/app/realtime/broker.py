from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "artbid:lot:"


class InProcessBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._loops: dict[int, asyncio.AbstractEventLoop] = {}

    async def publish(self, lot_public_id: str, message: dict[str, Any]) -> None:
        self._deliver(lot_public_id, message)

    def publish_threadsafe(self, lot_public_id: str, message: dict[str, Any]) -> None:
        self._deliver(lot_public_id, message)

    def _deliver(self, lot_public_id: str, message: dict[str, Any]) -> None:
        for queue in list(self._subscribers.get(lot_public_id, set())):
            loop = self._loops.get(id(queue))
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            if loop is not None and loop is not running:
                loop.call_soon_threadsafe(self._put, queue, message, lot_public_id)
            else:
                self._put(queue, message, lot_public_id)

    @staticmethod
    def _put(queue: asyncio.Queue, message: dict[str, Any], lot_public_id: str) -> None:
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning("sse_subscriber_slow", extra={"extra_fields": {"lotId": lot_public_id}})

    async def subscribe(self, lot_public_id: str) -> "InProcessSubscription":
        return InProcessSubscription(self, lot_public_id)

    def _attach(self, lot_public_id: str, queue: asyncio.Queue) -> None:
        try:
            self._loops[id(queue)] = asyncio.get_running_loop()
        except RuntimeError: 
            pass
        self._subscribers[lot_public_id].add(queue)

    def _detach(self, lot_public_id: str, queue: asyncio.Queue) -> None:
        self._subscribers[lot_public_id].discard(queue)
        self._loops.pop(id(queue), None)


class InProcessSubscription:
    def __init__(self, broker: InProcessBroker, lot_public_id: str) -> None:
        self.broker = broker
        self.lot_public_id = lot_public_id
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=500)

    async def __aenter__(self) -> "InProcessSubscription":
        self.broker._attach(self.lot_public_id, self.queue)
        return self

    async def __aexit__(self, *exc_info) -> None:
        self.broker._detach(self.lot_public_id, self.queue)

    async def get(self) -> dict[str, Any] | None:
        return await self.queue.get()


class RedisBroker:
    def __init__(self, url: str) -> None:
        self.url = url

    async def publish(self, lot_public_id: str, message: dict[str, Any]) -> None:
        from redis import asyncio as aioredis

        client = aioredis.from_url(self.url, socket_connect_timeout=1, socket_timeout=2)
        try:
            await client.publish(CHANNEL_PREFIX + lot_public_id, json.dumps(message, separators=(",", ":")))
        finally:
            await client.aclose()

    async def subscribe(self, lot_public_id: str) -> "RedisSubscription":
        return RedisSubscription(self.url, lot_public_id)


class RedisSubscription:
    def __init__(self, url: str, lot_public_id: str) -> None:
        self.url = url
        self.lot_public_id = lot_public_id
        self._client = None
        self._pubsub = None

    async def __aenter__(self) -> "RedisSubscription":
        from redis import asyncio as aioredis

        self._client = aioredis.from_url(
            self.url,
            socket_connect_timeout=1,
            socket_timeout=5,
            health_check_interval=15,
        )
        self._pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        await self._pubsub.subscribe(CHANNEL_PREFIX + self.lot_public_id)
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe(CHANNEL_PREFIX + self.lot_public_id)
                await self._pubsub.aclose()
            except Exception:  # pragma: no cover
                pass
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:  
                pass

    async def get(self, timeout: float | None = None) -> dict[str, Any] | None:
        message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
        if not message:
            return None
        try:
            return json.loads(message["data"])
        except Exception:  
            return None


_in_process_broker = InProcessBroker()


def get_broker() -> InProcessBroker | RedisBroker:
    if settings.redis_url:
        return RedisBroker(settings.redis_url)
    return _in_process_broker


def in_process_broker() -> InProcessBroker:
    return _in_process_broker


class ConnectionLimiter:
    def __init__(self, max_total: int, max_per_user: int) -> None:
        self.max_total = max_total
        self.max_per_user = max_per_user
        self._total = 0
        self._per_user: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, identity: str | None) -> bool:
        async with self._lock:
            if self._total >= self.max_total:
                return False
            key = identity or "anon"
            if self._per_user.get(key, 0) >= self.max_per_user:
                return False
            self._total += 1
            self._per_user[key] = self._per_user.get(key, 0) + 1
            return True

    async def release(self, identity: str | None) -> None:
        async with self._lock:
            key = identity or "anon"
            if self._per_user.get(key, 0) > 0:
                self._per_user[key] -= 1
                if self._per_user[key] == 0:
                    self._per_user.pop(key, None)
            if self._total > 0:
                self._total -= 1

    @property
    def active(self) -> int:
        return self._total


connection_limiter = ConnectionLimiter(settings.sse_max_connections, settings.sse_max_connections_per_user)
