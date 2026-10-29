"""Freno a la fuerza bruta: como mucho N intentos por clave en una ventana de tiempo.

Vive en memoria: basta para un solo servidor. Con varias instancias de Cloud Run cada una
llevaría su cuenta; si hiciera falta, se movería a la BD.
"""

import time
from collections import deque

from fastapi import HTTPException, status


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # Momentos de los últimos intentos de cada clave (p. ej. "ip|email").
        self.attempts: dict[str, deque[float]] = {}

    def hit(self, key: str) -> None:
        """Apunta un intento; 429 si ya se agotaron los de la ventana."""
        now = time.monotonic()
        recent = self.attempts.setdefault(key, deque())
        while recent and now - recent[0] > self.window_seconds:
            recent.popleft()
        if len(recent) >= self.max_attempts:
            minutes = max(1, round((self.window_seconds - (now - recent[0])) / 60))
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Demasiados intentos. Prueba de nuevo en {minutes} min.",
            )
        recent.append(now)

    def clear(self) -> None:
        self.attempts.clear()


# 10 intentos de login cada 15 minutos por IP + email.
LOGIN_LIMIT = RateLimiter(max_attempts=10, window_seconds=15 * 60)
# 3 emails de "recuperar contraseña" por hora y email (que nadie llene el buzón de otro).
RESET_LIMIT = RateLimiter(max_attempts=3, window_seconds=60 * 60)
