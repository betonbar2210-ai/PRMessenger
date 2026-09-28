import logging
import time

from django.core.cache.backends.redis import RedisCache
from redis.connection import ConnectionPool
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

logger = logging.getLogger(__name__)

RETRY_AFTER_SECONDS = 30.0

CONNECT_TIMEOUT_SECONDS = 0.5


class FailFastConnectionPool(ConnectionPool):
    def __init__(self, *args, **kwargs):
        kwargs["retry"] = Retry(NoBackoff(), 0)
        kwargs.setdefault("socket_connect_timeout", CONNECT_TIMEOUT_SECONDS)
        super().__init__(*args, **kwargs)


class ResilientRedisCache(RedisCache):
    _down_until = 0.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache._pool_class = FailFastConnectionPool

    @classmethod
    def _is_open(cls) -> bool:
        return time.monotonic() < cls._down_until

    @classmethod
    def _trip(cls) -> None:
        cls._down_until = time.monotonic() + RETRY_AFTER_SECONDS
        logger.warning(
            "Redis недоступен — кэширование временно отключено на %.0f с "
            "(сайт работает без кэша).",
            RETRY_AFTER_SECONDS,
        )

    def _miss(self, default, method, *args, **kwargs):
        if self._is_open():
            return default()
        try:
            result = method(*args, **kwargs)
        except RedisError:
            self._trip()
            return default()
        ResilientRedisCache._down_until = 0.0
        return result

    def get(self, key, default=None, version=None):
        return self._miss(lambda: default, super().get, key, default, version)

    def set(self, key, value, timeout=300, version=None):
        return self._miss(lambda: False, super().set, key, value, timeout, version)

    def add(self, key, value, timeout=300, version=None):
        return self._miss(lambda: False, super().add, key, value, timeout, version)

    def touch(self, key, timeout=300, version=None):
        return self._miss(lambda: False, super().touch, key, timeout, version)

    def delete(self, key, version=None):
        return self._miss(lambda: False, super().delete, key, version)

    def has_key(self, key, version=None):
        return self._miss(lambda: False, super().has_key, key, version)

    def get_many(self, keys, version=None):
        return self._miss(
            lambda: {key: None for key in keys}, super().get_many, keys, version
        )

    def set_many(self, data, timeout=300, version=None):
        return self._miss(lambda: [], super().set_many, data, timeout, version)

    def delete_many(self, keys, version=None):
        return self._miss(lambda: False, super().delete_many, keys, version)

    def incr(self, key, delta=1, version=None):
        return self._miss(lambda: None, super().incr, key, delta, version)

    def decr(self, key, delta=1, version=None):
        return self._miss(lambda: None, super().decr, key, delta, version)

    def clear(self, version=None):
        return self._miss(lambda: False, super().clear)

    def close(self, **kwargs):
        return self._miss(lambda: False, super().close, **kwargs)
