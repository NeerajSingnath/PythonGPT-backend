import asyncio
import threading
from typing import Any


class EventStream:

    def __init__(self):
        self._subscribers: dict[
            str,
            list[
                tuple[
                    asyncio.AbstractEventLoop,
                    asyncio.Queue,
                ]
            ],
        ] = {}

        self._lock = threading.RLock()

    def subscribe(
        self,
        run_id: str,
    ) -> asyncio.Queue:

        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        with self._lock:
            subscribers = self._subscribers.setdefault(
                run_id,
                [],
            )

            subscribers.append(
                (
                    loop,
                    queue,
                )
            )

        return queue

    def unsubscribe(
        self,
        run_id: str,
        queue: asyncio.Queue,
    ) -> None:

        with self._lock:
            subscribers = self._subscribers.get(run_id)

            if not subscribers:
                return

            self._subscribers[run_id] = [
                subscriber for subscriber in subscribers if subscriber[1] is not queue
            ]

            if not self._subscribers[run_id]:
                del self._subscribers[run_id]

    def publish(
        self,
        run_id: str,
        event: dict[str, Any],
    ) -> None:

        with self._lock:
            subscribers = list(self._subscribers.get(run_id, []))

        stale = []

        for loop, queue in subscribers:

            if loop.is_closed():
                stale.append(queue)
                continue

            loop.call_soon_threadsafe(
                self._put_event,
                queue,
                event,
            )

        for queue in stale:
            self.unsubscribe(
                run_id,
                queue,
            )

    def subscriber_count(
        self,
        run_id: str,
    ) -> int:

        with self._lock:
            return len(self._subscribers.get(run_id, []))

    @staticmethod
    def _put_event(
        queue: asyncio.Queue,
        event: dict[str, Any],
    ) -> None:

        queue.put_nowait(event)
