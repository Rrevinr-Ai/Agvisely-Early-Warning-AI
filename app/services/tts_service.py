import asyncio
import base64
import io

import edge_tts
from openai import OpenAI

from app.config import settings


class TTSService:
    def __init__(self) -> None:
        self.provider = settings.TTS_PROVIDER
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.TTS_MODEL
        self.voice = settings.TTS_VOICE

    async def _synthesize_edge(self, text: str) -> bytes:
        communicate = edge_tts.Communicate(text, self.voice)
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        return buffer.getvalue()

    def _synthesize_openai(self, text: str) -> bytes:
        if not self.client:
            raise ValueError("OPENAI_API_KEY is not configured")

        response = self.client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
        )
        return response.content

    async def synthesize_bytes_async(self, text: str) -> bytes:
        if self.provider == "edge":
            return await self._synthesize_edge(text)
        if self.provider == "openai":
            return self._synthesize_openai(text)
        raise ValueError(f"Unsupported TTS provider: {self.provider}")

    def synthesize_bytes(self, text: str) -> bytes:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.synthesize_bytes_async(text))

        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(self.synthesize_bytes_async(text))).result()

    def synthesize(self, text: str) -> str:
        return base64.b64encode(self.synthesize_bytes(text)).decode("utf-8")


tts_service = TTSService()
