from typing import Any

# Auto-split part 19: store_document
def store_document(user_id: int, doc: dict[str, Any]) -> bool:
    try:
        _execute_write(
            "INSERT OR IGNORE INTO v72_documents(user_id,name,sha256,size,kind,content) VALUES(?,?,?,?,?,?)",
            (int(user_id), doc["name"], doc["sha256"], int(doc["size"]), doc["kind"], doc["text"][:MAX_DOCUMENT_CHARS]),
        )
        return True
    except Exception:
        logger.exception("v72 document store failed")
        return False
