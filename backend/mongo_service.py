import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "brandconnect")
_database = None


def connect_mongodb():
    global _database

    if not MONGO_URI:
        return None

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        _database = client[MONGO_DB_NAME]
    except Exception:
        _database = None

    return _database


def get_database():
    return _database


def sync_creator(creator):
    if _database is None:
        return

    creator_document = dict(creator)
    creator_document["creator_id"] = creator_document.pop("id")
    _database.creators.update_one(
        {"creator_id": creator_document["creator_id"]},
        {"$set": creator_document},
        upsert=True,
    )
