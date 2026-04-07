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

        print("[Loading XTTS model...]")
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

        print("Reference path:", self.reference_audio_path)
        print("Exists:", os.path.exists(self.reference_audio_path))

    def clean_text(self, text: str) -> str:
        text = "" if text is None else str(text)

        replacements = {
            "\n": " ",
            "•": " ",
            "—": " ",
            "–": " ",
            "&": " و ",
            "%": " بالمئة",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Keep Arabic + numbers + punctuation
        text = re.sub(r"[^\u0600-\u06FF0-9\s\.؟!]", "", text)

        return re.sub(r"\s+", " ", text).strip()

    def split_text(self, text: str, max_len: int = 140) -> List[str]:
        sentences = re.split(r'[.!؟]+', text)

        chunks = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current) + len(sentence) < max_len:
                current += " " + sentence
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = sentence

        if current.strip():
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

    def generate_audio(self, text: str, out_path: str):
        text = self.clean_text(text)

        if not text.strip():
            print("[Warning] Empty text, skipping...")
            return

        chunks = self.split_text(text)

        chunks = [c.strip() for c in chunks if c.strip()]

        if not chunks:
            print("[Warning] No valid chunks, skipping...")
            return

        all_audio = []
        sample_rate = None

        for i, chunk in enumerate(chunks):
            temp_path = os.path.join(self.output_dir, f"temp_{i}.wav")

            print(f"  → Chunk {i+1}: {chunk[:60]}...")

            self.tts.tts_to_file(
                text=chunk,
                speaker_wav=self.reference_audio_path,
                language="ar",
                temperature=0.3,
                file_path=temp_path
            )

            audio, sr = sf.read(temp_path)

            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            if sample_rate is None:
                sample_rate = sr

            all_audio.append(audio)

            pause = np.zeros(int(0.25 * sr))
            all_audio.append(pause)

            os.remove(temp_path)

        final_audio = np.concatenate(all_audio)

        sf.write(out_path, final_audio.astype(np.float32), sample_rate)

    async def process_slide(self, slide: Dict[str, Any]):
        slide_id = slide["slide_id"]
        text = slide["text"]

        print(f"\n[Slide {slide_id}] Generating audio...")

        out_path = os.path.join(
            self.output_dir,
            f"slide_{slide_id}.wav"
        )

        self.generate_audio(text, out_path)

        print(f"[Saved] {out_path}")

    async def run_async(self, limit_slides: Optional[int] = None):
        slides = self.load_subtitles()

        if limit_slides:
            slides = slides[:limit_slides]

        print(f"[Speech] Processing {len(slides)} slides...")

        for slide in slides:
            await self.process_slide(slide)

        print("[DONE] Speech generation complete.")

    def run(self, limit_slides: Optional[int] = None):
        asyncio.run(self.run_async(limit_slides))

if __name__ == "__main__":
    agent = SpeechAgent()
    agent.run()