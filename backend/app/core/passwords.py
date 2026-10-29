"""Contraseñas: se guardan como hash argon2, nunca en claro."""

from pwdlib import PasswordHash

# argon2id con los parámetros recomendados por pwdlib (lento a propósito: frena la fuerza bruta).
PASSWORD_HASH = PasswordHash.recommended()
# Hash de una contraseña que nadie usa. Si el email no existe se verifica contra este, para que
# "no existe" y "contraseña mal" tarden lo mismo y no se pueda averiguar qué emails tienen cuenta.
DUMMY_HASH = PASSWORD_HASH.hash("contraseña-ficticia-para-igualar-tiempos")


def hash_password(password: str) -> str:
    return PASSWORD_HASH.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """True si la contraseña es la del hash. Sin hash (cuenta solo de Google) siempre es False."""
    if password_hash is None:
        PASSWORD_HASH.verify(password, DUMMY_HASH)
        return False
    return PASSWORD_HASH.verify(password, password_hash)
