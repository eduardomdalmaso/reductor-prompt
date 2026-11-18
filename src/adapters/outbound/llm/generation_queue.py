import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional


class QueueSaturatedError(RuntimeError):
    """Lançada quando a fila de geração atinge o limite máximo de requisições pendentes."""


class QueueTimeoutError(TimeoutError):
    """Lançada quando uma requisição excede o tempo máximo de espera na fila."""


class QueueCancelledError(RuntimeError):
    """Lançada quando o cliente desconecta enquanto a requisição aguarda na fila."""


class GenerationQueue:
    """Fila controlada para limitar gerações simultâneas na GPU com cancelamento cooperativo e métricas."""

    def __init__(
        self,
        max_concurrent: int = 1,
        max_pending: int = 12,
        acquire_timeout_s: float = 45.0,
    ):
        self.max_concurrent = max(1, max_concurrent)
        self.max_pending = max(0, max_pending)
        self.acquire_timeout_s = max(0.5, acquire_timeout_s)
        self._sem = threading.Semaphore(self.max_concurrent)
        self._lock = threading.Lock()
        self._active = 0
        self._pending = 0
        self._total_acquired = 0
        self._total_rejected = 0
        self._total_timeouts = 0
        self._total_cancelled = 0
        self._total_wait_ms = 0.0
        self._max_wait_ms = 0.0
        self._last_wait_ms = 0.0
        self._total_gen_s = 0.0
        self._max_gen_s = 0.0
        self._last_gen_s = 0.0

    @contextmanager
    def slot(self, is_cancelled: Optional[Callable[[], bool]] = None):
        with self._lock:
            if self._pending >= self.max_pending and self._active >= self.max_concurrent:
                self._total_rejected += 1
                raise QueueSaturatedError(
                    f"Fila de geração saturada ({self._active} ativas, {self._pending} pendentes)."
                )
            self._pending += 1

        t_wait = time.perf_counter()
        acquired = False
        t_gen_start = 0.0
        try:
            deadline = t_wait + self.acquire_timeout_s
            while True:
                if is_cancelled and is_cancelled():
                    with self._lock:
                        self._pending = max(0, self._pending - 1)
                        self._total_cancelled += 1
                    raise QueueCancelledError("Requisição cancelada pelo cliente enquanto aguardava na fila.")

                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    with self._lock:
                        self._pending = max(0, self._pending - 1)
                        self._total_timeouts += 1
                    raise QueueTimeoutError(
                        f"Timeout de {self.acquire_timeout_s}s aguardando slot na fila de geração."
                    )

                if self._sem.acquire(timeout=min(0.1, remaining)):
                    acquired = True
                    break

            wait_ms = (time.perf_counter() - t_wait) * 1000.0
            with self._lock:
                self._pending = max(0, self._pending - 1)
                self._active += 1
                self._total_acquired += 1
                self._last_wait_ms = round(wait_ms, 2)
                self._total_wait_ms += wait_ms
                if wait_ms > self._max_wait_ms:
                    self._max_wait_ms = round(wait_ms, 2)
            t_gen_start = time.perf_counter()
            yield round(wait_ms, 2)
        except Exception:
            if not acquired:
                with self._lock:
                    if self._pending > 0:
                        self._pending -= 1
            raise
        finally:
            if acquired:
                gen_s = time.perf_counter() - t_gen_start if t_gen_start else 0.0
                with self._lock:
                    self._active = max(0, self._active - 1)
                    self._last_gen_s = round(gen_s, 4)
                    self._total_gen_s += gen_s
                    if gen_s > self._max_gen_s:
                        self._max_gen_s = round(gen_s, 4)
                self._sem.release()

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            avg_wait = (
                round(self._total_wait_ms / self._total_acquired, 2)
                if self._total_acquired > 0
                else 0.0
            )
            avg_gen_s = (
                round(self._total_gen_s / self._total_acquired, 4)
                if self._total_acquired > 0
                else 0.0
            )
            return {
                "max_concurrent": self.max_concurrent,
                "max_pending": self.max_pending,
                "acquire_timeout_s": self.acquire_timeout_s,
                "generation_active": self._active,
                "generation_pending": self._pending,
                "total_acquired": self._total_acquired,
                "generation_rejected_total": self._total_rejected,
                "generation_timeout_total": self._total_timeouts,
                "generation_cancelled_total": self._total_cancelled,
                "generation_queue_wait_seconds": {
                    "avg": round(avg_wait / 1000.0, 4),
                    "max": round(self._max_wait_ms / 1000.0, 4),
                    "last": round(self._last_wait_ms / 1000.0, 4),
                },
                "generation_duration_seconds": {
                    "avg": avg_gen_s,
                    "max": self._max_gen_s,
                    "last": self._last_gen_s,
                },
            }
