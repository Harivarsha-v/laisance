"""MongoDB access for the assistant's chat logs and feedback.

Connects lazily using MONGODB_URI. If MongoDB is not configured or not
reachable, documents are appended to logs/<collection>.jsonl instead so the
site keeps working; the health page reports which store is in use.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from django.conf import settings

log = logging.getLogger("laisance")
_client = None
_last_error = ""


def _db():
    global _client, _last_error
    if not settings.MONGODB_URI:
        _last_error = "MONGODB_URI not set"
        return None
    try:
        if _client is None:
            from pymongo import MongoClient

            _client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                                  connectTimeoutMS=settings.MONGODB_TIMEOUT_MS, appname="laisance")
        return _client[settings.MONGODB_DB]
    except Exception as exc:  # bad URI etc.
        _last_error = str(exc)[:200]
        log.warning("MongoDB unavailable: %s", exc)
        return None


def _fallback(collection, doc):
    path = settings.LOG_DIR / f"{collection}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, default=str) + "\n")


def insert(collection, doc):
    """Insert a document; returns (id, store) where store is 'mongodb' or 'file'."""
    global _last_error
    doc = {**doc, "created_at": datetime.now(timezone.utc)}
    db = _db()
    if db is not None:
        try:
            return str(db[collection].insert_one(doc).inserted_id), "mongodb"
        except Exception as exc:
            _last_error = str(exc)[:200]
            log.warning("MongoDB insert failed, using file fallback: %s", exc)
    doc["_id"] = uuid.uuid4().hex
    _fallback(collection, doc)
    return doc["_id"], "file"


def update(collection, doc_id, fields):
    db = _db()
    if db is not None:
        try:
            from bson import ObjectId

            key = ObjectId(doc_id) if ObjectId.is_valid(doc_id) else doc_id
            db[collection].update_one({"_id": key}, {"$set": fields})
            return "mongodb"
        except Exception as exc:
            log.warning("MongoDB update failed: %s", exc)
    _fallback(collection, {"_id": doc_id, "update": fields, "at": datetime.now(timezone.utc)})
    return "file"


def status():
    """For the health page: {'ok': bool, 'store': ..., 'detail': ..., 'counts': {...}}."""
    db = _db()
    if db is None:
        return {"ok": False, "store": "file fallback", "detail": _last_error or "not configured", "counts": {}}
    try:
        db.command("ping")
        counts = {c: db[c].estimated_document_count() for c in ("chat_logs", "feedback")}
        return {"ok": True, "store": "mongodb", "detail": f"connected to {settings.MONGODB_DB}", "counts": counts}
    except Exception as exc:
        return {"ok": False, "store": "file fallback", "detail": str(exc)[:160], "counts": {}}
