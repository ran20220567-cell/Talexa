import os
import re
import json
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
import soundfile as sf
from TTS.api import TTS


class SpeechAgent:
    def __init__(
        self,
        subtitles_json_path: str = "Data/intermediate/subtitles.json",
        reference_audio_path: str = "Data/input/reference_voice.wav",
        output_dir: str = "Data/intermediate/speech_arabic/lecture1",
    ):
        self.subtitles_json_path = subtitles_json_path
        self.reference_audio_path = os.path.abspath(reference_audio_path)
        self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)

        print("[Loading XTTS-v2 model...]")
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

        print("Reference path:", self.reference_audio_path)
        print("Exists:", os.path.exists(self.reference_audio_path))

        self.speaker_wav = self.reference_audio_path

    def clean_text(self, text: str) -> str:
        text = "" if text is None else str(text)

        text = text.replace("\n", " ")

        text = re.sub(r"[^\u0600-\u06FF0-9\s\.؟!،]", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def split_text(self, text: str, max_len: int = 250) -> List[str]:
        sentences = re.split(r"[.!؟]+", text)

        chunks = []
        current = ""

        for s in sentences:
            s = s.strip()
            if not s:
                continue

            if len(current) + len(s) < max_len:
                current += " " + s
            else:
                if current:
                    chunks.append(current.strip())
                current = s

        if current:
            chunks.append(current.strip())

        return chunks

    def load_subtitles(self) -> List[Dict[str, Any]]:
        with open(self.subtitles_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        slides = []

        for key in sorted(data.keys()):
            slide = data[key]

            text = " ".join(
                self.clean_text(i.get("sentence", ""))
                for i in slide.get("items", [])
            )

            slides.append({
                "slide_id": slide.get("slide_number", key),
                "text": text
            })

        return slides

    def generate_chunk(self, chunk: str):
        wav = self.tts.tts(
            text=chunk,
            language="ar",

            speaker_wav=self.speaker_wav,

            temperature=0.2,
            length_penalty=1.0
        )

        return np.array(wav), 24000

    def generate_audio(self, text: str, out_path: str):
        text = self.clean_text(text)

        if not text.strip():
            return

        chunks = self.split_text(text)

        all_audio = []
        sr = 24000

        for i, chunk in enumerate(chunks):
            print(f"  → Chunk {i+1}: {chunk[:60]}...")

            audio, sr = self.generate_chunk(chunk)

            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            all_audio.append(audio)

            # small pause to avoid merging artifacts
            all_audio.append(np.zeros(int(0.15 * sr)))

        final_audio = np.concatenate(all_audio)

        sf.write(out_path, final_audio.astype(np.float32), sr)

    async def process_slide(self, slide: Dict[str, Any]):
        slide_id = slide["slide_id"]

        print(f"\n[Slide {slide_id}] Generating audio...")

        out_path = os.path.join(self.output_dir, f"slide_{slide_id}.wav")

        self.generate_audio(slide["text"], out_path)

        print(f"[Saved] {out_path}")

    async def run_async(self, limit_slides: Optional[int] = None):
        slides = self.load_subtitles()

        if limit_slides:
            slides = slides[:limit_slides]

        print(f"[Speech] Processing {len(slides)} slides...")

        for slide in slides:
            await self.process_slide(slide)

        print("[DONE]")

    def run(self, limit_slides: Optional[int] = None):
        asyncio.run(self.run_async(limit_slides))


if __name__ == "__main__":
    agent = SpeechAgent()
    agent.run()
