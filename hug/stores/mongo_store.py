from pymongo import MongoClient
import logging
import uuid

class MongoDBStore:
    def __init__(self, uri='mongodb://localhost:27017/', db_name='session_db', collection_name='sessions', ttl=3600, logger=None):
        self._logger = logger if logger is not None else logging.getLogger("hug")
        self._client = MongoClient(uri)
        self._collection = self._client[db_name][collection_name]
        self._collection.create_index("createdAt", expireAfterSeconds=ttl)

    def get(self, key):
        try:
            return self._collection.find_one({"_id": key}) or {}
        except Exception as e:
            self._logger.exception("MongoDB exception: {}".format(str(e)))
            return {}

    def set(self, key, data):
        try:
            data['createdAt'] = uuid.uuid1().time
            self._collection.update_one({"_id": key}, {"$set": data}, upsert=True)
        except Exception as e:
            self._logger.exception("MongoDB exception: {}".format(str(e)))
            raise

    def exists(self, key):
        try:
            return self._collection.count_documents({"_id": key}, limit=1) > 0
        except Exception as e:
            self._logger.exception("MongoDB exception: {}".format(str(e)))
            raise
        

    def delete(self, key):
        try:
            self._collection.delete_one({"_id": key})
        except Exception as e:
            self._logger.exception("MongoDB exception: {}".format(str(e)))
            raise