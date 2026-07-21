import time
from collections.abc import Callable
from typing import Any


def smart_wait(
    function: Callable[[], Any],
    expected_result: Callable[[Any], bool],
    timeout: float = 10,
    interval: float = 0.5,
) -> Any:
    deadline = time.monotonic() + timeout
    last_value = None
    while time.monotonic() < deadline:
        last_value = function()
        if expected_result(last_value):
            return last_value
        time.sleep(interval)
    raise TimeoutError(f"condition not met within {timeout}s, last seen: {last_value!r}")
