"""Bounded concurrent producers for the synchronous WSGI streaming consumer."""
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty, Full
from threading import Event, BoundedSemaphore
import logging
import time

log = logging.getLogger(__name__)
# Prepared routes cannot queue behind RAPTOR or public pedestrian requests.
PREPARED = ThreadPoolExecutor(max_workers=4, thread_name_prefix='pap-prepared')
BACKGROUND = ThreadPoolExecutor(max_workers=8, thread_name_prefix='pap-routing')
PREPARED_SLOTS = BoundedSemaphore(16)
BACKGROUND_SLOTS = BoundedSemaphore(24)


def merge(factories, *, timeout=30, heartbeat=1):
    """Factories own/close their connections in their worker; never share SQLite.

    Yields (source, result, finished). Errors and capacity exhaustion remain
    explicit incomplete searches. Closing the consumer cancels queued work;
    running generators stop cooperatively at their next publication boundary.
    """
    messages = Queue(maxsize=16)
    stopped = Event()
    futures = []
    pending = set(factories)
    deadline = time.monotonic() + timeout

    def publish(message):
        while not stopped.is_set():
            try:
                messages.put(message, timeout=.05)
                return
            except Full:
                pass

    def produce(name, factory):
        stream = None
        try:
            if stopped.is_set():return
            stream = factory()
            for result in stream:
                if stopped.is_set():break
                publish((name, result, False))
                if result.get('complete'):break
        except Exception:
            log.exception('Route source failed: %s', name)
            publish((name, {'journeys': [], 'search_limited': True,
                            'optimal_within_limits': False, 'failed_sources': [name]}, False))
        finally:
            try:
                if stream is not None:stream.close()
            finally:
                publish((name, None, True))

    try:
        for name, factory in factories.items():
            pool, slots = (PREPARED, PREPARED_SLOTS) if name in ('prepared', 'legacy_prepared') else (BACKGROUND, BACKGROUND_SLOTS)
            if not slots.acquire(blocking=False):
                pending.remove(name)
                yield name, {'journeys': [], 'search_limited': True,
                             'optimal_within_limits': False, 'busy_sources': [name]}, False
                continue
            try:
                future = pool.submit(produce, name, factory)
            except BaseException:
                slots.release()
                raise
            future.add_done_callback(lambda _, slots=slots: slots.release())
            futures.append(future)
        while pending:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                for name in sorted(pending):
                    yield name, {'journeys': [], 'search_limited': True,
                                 'optimal_within_limits': False, 'timed_out_sources': [name]}, False
                break
            try:
                name, result, done = messages.get(timeout=min(heartbeat, remaining))
            except Empty:
                yield None, None, False
                continue
            if done:pending.discard(name)
            elif result is not None:yield name, result, False
        stopped.set()
        for future in futures:future.cancel()
        yield None, None, True
    finally:
        stopped.set()
        for future in futures:future.cancel()
