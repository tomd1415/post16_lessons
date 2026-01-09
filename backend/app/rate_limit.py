import time


def compute_lock_seconds(failed_count: int) -> int:
    if failed_count < 3:
        return 0
    if failed_count < 5:
        return 30
    if failed_count < 7:
        return 120
    if failed_count < 9:
        return 300
    return 600


class LoginLimiter:
    def __init__(self):
        self._state = {}

    def check(self, key: str) -> int:
        info = self._state.get(key)
        if not info:
            return 0
        _, locked_until = info
        if locked_until and locked_until > time.time():
            return int(locked_until - time.time())
        return 0

    def record_failure(self, key: str) -> int:
        count, locked_until = self._state.get(key, (0, 0))
        count += 1
        lock_seconds = compute_lock_seconds(count)
        locked_until = time.time() + lock_seconds if lock_seconds else 0
        self._state[key] = (count, locked_until)
        return lock_seconds

    def reset(self, key: str) -> None:
        self._state.pop(key, None)
