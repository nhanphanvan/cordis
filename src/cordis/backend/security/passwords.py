import base64
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 100_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return (
        f"pbkdf2_sha256${iterations}$"
        f"{base64.urlsafe_b64encode(salt).decode('utf-8')}$"
        f"{base64.urlsafe_b64encode(digest).decode('utf-8')}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    algorithm, raw_iterations, encoded_salt, encoded_digest = password_hash.split("$", maxsplit=3)
    if algorithm != "pbkdf2_sha256":
        return False

    iterations = int(raw_iterations)
    salt = base64.urlsafe_b64decode(encoded_salt.encode("utf-8"))
    expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("utf-8"))
    candidate_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate_digest, expected_digest)
