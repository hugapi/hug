import redis
import logging

class RedisStore:
    def __init__(self, host='localhost', port=6379, db=0, ttl=3600, logger=None):
        self._logger = logger if logger is not None else logging.getLogger("hug")
        self._client = redis.StrictRedis(host=host, port=port, db=db, decode_responses=True)
        self._ttl = ttl

    def get(self, key):
        try:
            return self._client.hgetall(key)
        except redis.RedisError as e:
            self._logger.exception("Redis Error: {}".format(str(e)))
            return {}
        except Exception as e:
            self._logger.exception("Redis Exception: {}".format(str(e)))
            return {}

    def set(self, key, data):
        try:
            self._client.hmset(key, data)
            self._client.expire(key, self._ttl)
        except redis.RedisError as e:
            self._logger.exception("Redis Error: {}".format(str(e)))
            raise
        except Exception as e:
            self._logger.exception("Redis Exception: {}".format(str(e)))
            raise

    def exists(self, key):
        try:
            return self._client.exists(key)
        except redis.RedisError as e:
            self._logger.exception("Redis Error: {}".format(str(e)))
            raise
        except Exception as e:
            self._logger.exception("Redis Exception: {}".format(str(e)))
            raise

    def delete(self, key):
        try:
            self._client.delete(key)
        except redis.RedisError as e:
            self._logger.exception("Redis Error: {}".format(str(e)))
            raise
        except Exception as e:
            self._logger.exception("Redis Exception: {}".format(str(e)))
            raise
        