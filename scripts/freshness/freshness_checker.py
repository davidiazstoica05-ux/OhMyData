def is_unchanged(stored, remote_etag, new_hash):
    """Decide whether a page changed. Pure decision: it never writes to the DB.

    stored: dict returned by pages.get_page_state().
    remote_etag: ETag sent by the origin server (None if it sent none).
    new_hash: hash of the freshly downloaded content, computed over the
              STEMMED text so formatting changes do not count as changes.
    """
    # 1. ETag: if the server sent one and it matches the stored one,
    #    the page has not changed (the equivalent of a 304 response)
    if remote_etag is not None and remote_etag == stored["etag"]:
        return True

    # 2. Hash: same stemmed content means no real change. A snippet-only
    #    page has no hash (None), so it can never match here.
    if stored["content_hash"] is not None and stored["content_hash"] == new_hash:
        return True

    # Different or missing hash: changed (or snippet-only), so replace it
    return False