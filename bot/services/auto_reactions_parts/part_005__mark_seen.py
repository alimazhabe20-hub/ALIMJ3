# Auto-split part 5: _mark_seen
def _mark_seen(key: tuple[int, int]) -> bool:
    if key in _recent_set:
        return False
    if len(_recent_messages) == _recent_messages.maxlen:
        _recent_set.discard(_recent_messages[0])
    _recent_messages.append(key)
    _recent_set.add(key)
    return True
