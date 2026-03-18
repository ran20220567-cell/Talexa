import os
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

import ollama

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Prompts.subtitle_cursor_prompt import SUBTITLE_CURSOR_PROMPT


class SubtitleCursorAgent:

    def __init__(
        self,
        model_name="qwen3-vl:8b",
        output_path="Data/intermediate/subtitles.json",
    ):
        self.model_name = model_name
        self.output_path = output_path
        self.system_prompt = SUBTITLE_CURSOR_PROMPT.strip()
        self.client = ollama.Client()

        self.banned_patterns = [
            r"^this slide",
            r"^the slide",
            r"^here we see",
            r"^it mentions",
            r"^the date",
            r"^the location",
            r"^the definition is provided",
            r"^the slide is titled",
        ]

    def _extract_slide_number(self, file_path):
        name = os.path.basename(file_path)
        nums = re.findall(r"\d+", name)
        return int(nums[-1]) if nums else 0

    def get_slide_images(self, folder):

        if not os.path.exists(folder):
            raise FileNotFoundError(folder)

        images = []

        for f in os.listdir(folder):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                images.append(os.path.join(folder, f))

        images.sort(key=self._extract_slide_number)

        return images

    def _is_bad_sentence(self, sentence):

        s = sentence.lower().strip()

        if len(sentence.split()) < 6:
            return True

        for pattern in self.banned_patterns:
            if re.match(pattern, s):
                return True

        return False

    def _clean_json(self, text):

        text = text.strip()

        text = re.sub(r"^```(?:json)?", "", text)
        text = re.sub(r"```$", "", text)

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            text = text[start:end+1]

        return text


    def parse_output(self, raw_text):

        cleaned = self._clean_json(raw_text)

        try:
            data = json.loads(cleaned)

            valid_items = []

            for item in data.get("sentences", []):

                sentence = item.get("sentence", "").strip()
                focus = item.get("focus", "").strip()

                if not sentence or not focus:
                    continue

                if self._is_bad_sentence(sentence):
                    continue

                valid_items.append({
                    "sentence": sentence,
                    "focus": focus
                })

            if not valid_items:
                raise ValueError

            return valid_items

        except:
            return [{
                "sentence": "This slide introduces an important concept which is explained through the visible content.",
                "focus": "main title and central slide content"
            }]

    def generate_for_slide(self, image_path, slide_index):

        print(f"Processing slide {slide_index}")

        response = self.client.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": f"Analyze slide {slide_index} and generate lecture explanation.",
                    "images": [image_path]
                }
            ]
        )

        raw = response["message"]["content"]

        parsed = self.parse_output(raw)

        return parsed

    def run(self, slide_folder):

        images = self.get_slide_images(slide_folder)

        results = {}

        for i, img in enumerate(images, start=1):

            items = self.generate_for_slide(img, i)

            results[f"slide_{i}"] = {
                "slide_number": i,
                "image": img,
                "items": items
            }

        Path(os.path.dirname(self.output_path)).mkdir(parents=True, exist_ok=True)

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print("\nSaved:", self.output_path)


if __name__ == "__main__":

    agent = SubtitleCursorAgent()

    agent.run("Data/intermediate/lecture1_slides")
