# Auto-split part 2: get_schema_status
def get_schema_status() -> dict[str, object]:
    """Return safe database schema metadata for diagnostics and tests."""
    conn = get_db_connection()
    try:
        return schema_status(conn)
    finally:
        conn.close()
