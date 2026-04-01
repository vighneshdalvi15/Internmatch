from __future__ import annotations

from bson import ObjectId


def oid(value: str) -> ObjectId:
    return ObjectId(value)


def str_oid(value: ObjectId) -> str:
    return str(value)


def _serialize_value(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, list):
        return [_serialize_value(x) for x in v]
    if isinstance(v, dict):
        return serialize_doc(v)
    return v


def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    out = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = str(v)
        else:
            out[k] = _serialize_value(v)
    return out

