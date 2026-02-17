"""
Utilitários de senha (sem dependência do Streamlit).
Usado pela API FastAPI e scripts de seed.
"""
import hashlib
import secrets


def hash_password(password: str) -> str:
    """Gera hash da senha usando SHA-256 com salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica se a senha está correta"""
    try:
        salt, stored_hash = password_hash.split(":")
        password_hash_check = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash_check == stored_hash
    except ValueError:
        return False
