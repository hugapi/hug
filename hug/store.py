from hug.stores.inmemory_store import InMemoryStore
from hug.stores.redis_store import RedisStore
from hug.stores.mongo_store import MongoDBStore
from hug.stores.sql_store import SQLStore

class StoreWrapper:
    def __init__(self, store_type='inmemory', **kwargs):
        if store_type == 'redis':
            self.store = RedisStore(**kwargs)
        elif store_type == 'mongodb':
            self.store = MongoDBStore(**kwargs)
        elif store_type == 'sql':
            self.store = SQLStore(**kwargs)
        else:
            self.store = InMemoryStore(**kwargs)

    def get(self, key):
        return self.store.get(key)

    def set(self, key, data):
        self.store.set(key, data)

    def exists(self, key):
        return self.store.exists(key)

    def delete(self, key):
        self.store.delete(key)