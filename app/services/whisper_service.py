import base64
import io
import re
import struct
import subprocess

from openai import OpenAI

from app.config import settings

BANGLA_STYLE_PROMPT = "আজকের আবহাওয়া কেমন? ধানের পরামর্শ দিন।"

GPT4O_BANGLA_PROMPT = (
    "Transcribe the farmer's speech once in Bangla (বাংলা). "
    "Do not repeat phrases. Output only the spoken words, nothing else."
)


def _collapse_repetition(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return cleaned

    # Entire string is the same short phrase repeated many times.
    length = len(cleaned)
    for size in range(length // 2, 7, -1):
        chunk = cleaned[:size]
        if len(chunk) < 8:
            break
        if chunk * (length // size) == cleaned[: (length // size) * size]:
            return chunk.strip()
        if cleaned.count(chunk) >= 3 and cleaned.count(chunk) * len(chunk) >= length * 0.55:
            return chunk.strip()

    # Same clause repeated with spaces (word-level).
    words = cleaned.split()
    if len(words) >= 8:
        for chunk_words in range(len(words) // 2, 3, -1):
            chunk = " ".join(words[:chunk_words])
            if cleaned.count(chunk) >= 3:
                return chunk.strip()

    return cleaned


def _is_repetitive_hallucination(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) < 20:
        return False

    collapsed = _collapse_repetition(cleaned)
    if collapsed != cleaned and len(collapsed) < len(cleaned) * 0.45:
        return True

    words = cleaned.split()
    if len(words) >= 6:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.45:
            return True

    return False


def _wav_rms(wav_bytes: bytes) -> float:
    if len(wav_bytes) <= 44:
        return 0.0
    samples = struct.unpack(f"<{(len(wav_bytes) - 44) // 2}h", wav_bytes[44:])
    if not samples:
        return 0.0
    mean_sq = sum(s * s for s in samples) / len(samples)
    return (mean_sq**0.5) / 32768.0


class WhisperService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.WHISPER_MODEL

    def _uses_gpt4o_transcribe(self) -> bool:
        return "gpt-4o" in self.model

    def _to_wav(self, audio_bytes: bytes) -> bytes:
        if audio_bytes[:4] == b"RIFF":
            wav_bytes = audio_bytes
        else:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-loglevel",
                    "error",
                    "-i",
                    "pipe:0",
                    "-af",
                    (
                        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.3:"
                        "stop_periods=1:stop_threshold=-45dB:stop_silence=0.4,"
                        "highpass=f=100,lowpass=f=7000,volume=3dB,"
                        "loudnorm=I=-16:TP=-1.5:LRA=11"
                    ),
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-f",
                    "wav",
                    "pipe:1",
                ],
                input=audio_bytes,
                capture_output=True,
                timeout=15,
            )
            if result.returncode != 0:
                raise ValueError("অডিও পড়া যায়নি — আবার রেকording করুন")
            wav_bytes = result.stdout

        if _wav_rms(wav_bytes) < 0.008:
            raise ValueError("অডিও খুব নিঃশব্দ — মাইকের কাছে স্পষ্ট করে আবার বলুন")
        return wav_bytes

    def _sanitize_transcript(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text.strip())
        if not cleaned:
            raise ValueError("শুনতে পারিনি — আবার বলুন")

        if _is_repetitive_hallucination(cleaned):
            raise ValueError(
                "অডিও স্পষ্ট শোনা যায়নি — ২-৩ সেকেন্ড একবার বলুন, তারপর থামান"
            )

        return cleaned

    def transcribe(self, audio_base64: str, language: str | None = None) -> str:
        if not self.client:
            raise ValueError("OPENAI_API_KEY is not configured")

        audio_bytes = base64.b64decode(audio_base64)
        if len(audio_bytes) < 1000:
            raise ValueError("অডিও খুব ছোট — আরেকটু বলুন")

        try:
            wav_bytes = self._to_wav(audio_bytes)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("অডিও প্রসেস করা যায়নি — আবার রেকording করুন") from exc

        if len(wav_bytes) < 3200:
            raise ValueError("অডিও খুব ছোট — আরেকটু বলুন")

        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "audio.wav"

        kwargs: dict = {
            "model": self.model,
            "file": audio_file,
            "temperature": 0,
        }

        if self._uses_gpt4o_transcribe():
            kwargs["prompt"] = GPT4O_BANGLA_PROMPT
            kwargs["language"] = language or "bn"
        else:
            kwargs["prompt"] = BANGLA_STYLE_PROMPT

        result = self.client.audio.transcriptions.create(**kwargs)
        return self._sanitize_transcript(result.text)


whisper_service = WhisperService()
