import os
import re
import json
import asyncio
from typing import List, Dict, Any, Optional
from elevenlabs import ElevenLabs, save
from pydub import AudioSegment


class SpeechAgent:
    def __init__(
        self,
        subtitles_json_path: str = "Data/intermediate/subtitles.json",
        output_dir: str = "Data/intermediate/speech/lecture1",
        api_key: str = "sk_750e0572c5fc6d7cc3920d7ab0ee832dc1b209cd8ffe37ef",
        voice_id: str = "aoEJEWeOt9DoaRRQTNaB",
    ):
        self.subtitles_json_path = subtitles_json_path
        self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)

        self.api_key = api_key or os.getenv("sk_750e0572c5fc6d7cc3920d7ab0ee832dc1b209cd8ffe37ef")
        self.voice_id = voice_id or os.getenv("aoEJEWeOt9DoaRRQTNaB")

        if not self.api_key or not self.voice_id:
            raise ValueError("API key or Voice ID missing")

        self.client = ElevenLabs(api_key=self.api_key)

        print("[ElevenLabs TTS Loaded]")
        print("Output dir:", self.output_dir)

    def clean_text(self, text: str) -> str:
        """
        Safe cleaning: supports Arabic + English + mixed text
        """
        if text is None:
            return ""

        text = str(text)

        text = text.replace("\n", " ")

        text = re.sub(r"[^\u0600-\u06FFA-Za-z0-9\s\.\?!،]", "", text)

        text = re.sub(r"\s+", " ", text).strip()

        return text

    def split_text(self, text: str, max_len: int = 250) -> List[str]:
        """
        Splits text into chunks without breaking sentences
        """
        sentences = re.split(r"[.!?؟]+", text)

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

    def generate_chunk(self, chunk: str, out_file: str):
        audio = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=chunk,
            model_id="eleven_multilingual_v2"
        )

        save(audio, out_file)

    def generate_audio(self, text: str, out_path: str):
        text = self.clean_text(text)

        if not text.strip():
            print("[Skipped empty text]")
            return

        chunks = self.split_text(text)

        temp_files = []

        for i, chunk in enumerate(chunks):
            print(f"  → Chunk {i+1}/{len(chunks)}")

            tmp_file = os.path.join(self.output_dir, f"tmp_{i}.mp3")

            self.generate_chunk(chunk, tmp_file)

            temp_files.append(tmp_file)

        combined = AudioSegment.empty()

        for f in temp_files:
            audio = AudioSegment.from_file(f)
            combined += audio
            combined += AudioSegment.silent(duration=150)

        combined.export(out_path, format="wav")

        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

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