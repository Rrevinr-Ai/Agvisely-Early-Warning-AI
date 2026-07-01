import uuid
from datetime import datetime, timedelta

_audio_cache: dict[str, tuple[bytes, datetime]] = {}
_CACHE_TTL = timedelta(minutes=10)


def store_audio(audio_bytes: bytes) -> str:
    token = uuid.uuid4().hex
    _audio_cache[token] = (audio_bytes, datetime.utcnow())
    _cleanup_cache()
    return token


def get_audio(token: str) -> bytes | None:
    entry = _audio_cache.get(token)
    if not entry:
        return None
    audio_bytes, created_at = entry
    if datetime.utcnow() - created_at > _CACHE_TTL:
        _audio_cache.pop(token, None)
        return None
    return audio_bytes


def _cleanup_cache() -> None:
    now = datetime.utcnow()
    expired = [
        token
        for token, (_, created_at) in _audio_cache.items()
        if now - created_at > _CACHE_TTL
    ]
    for token in expired:
        _audio_cache.pop(token, None)
