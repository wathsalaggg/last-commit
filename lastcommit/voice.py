"""Give the ghost a voice with ElevenLabs text-to-speech."""

from pathlib import Path

from . import config
from .http import request

API = "https://api.elevenlabs.io/v1/text-to-speech"


def speak(text: str, out_path: Path) -> Path:
    key = config.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    voice = config.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    model = config.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
    _, _, audio = request(
        f"{API}/{voice}?output_format=mp3_44100_128",
        method="POST",
        headers={"xi-api-key": key, "Accept": "audio/mpeg"},
        body={
            "text": text,
            "model_id": model,
            # Lower stability = more breathy, uneven delivery. Suits a ghost.
            "voice_settings": {"stability": 0.35, "similarity_boost": 0.75,
                               "style": 0.4, "use_speaker_boost": True},
        },
        timeout=180,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    return out_path
