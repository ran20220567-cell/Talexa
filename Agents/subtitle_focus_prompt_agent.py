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
    """
    Talexa Subtitle + Cursor Focus Agent

    Input:
        data/intermediate/slide_images/

    Output:
        data/output/subtitles.json

    Each slide gets:
        - spoken presentation sentences
        - one precise cursor focus prompt per sentence
    """

    def __init__(
        self,
        model_name: str = "qwen2.5vl:7b",
        output_path: str = "data/output/subtitles.json",
        ollama_host: str | None = None,
    ):
        self.model_name = model_name
        self.output_path = output_path
        self.system_prompt = SUBTITLE_CURSOR_PROMPT.strip()

        if ollama_host:
            self.client = ollama.Client(host=ollama_host)
        else:
            self.client = ollama.Client()

    def _extract_slide_number(self, file_path: str) -> int:
        """
        Extract numeric order from filename.
        Examples:
            slide_1.png -> 1
            page12.jpg -> 12
            my_slide_003.png -> 3
        """
        filename = os.path.basename(file_path)
        nums = re.findall(r"\d+", filename)
        return int(nums[-1]) if nums else 0

    def get_slide_images(self, slide_imgs_dir: str) -> List[str]:
        if not os.path.exists(slide_imgs_dir):
            raise FileNotFoundError(f"Slide image folder not found: {slide_imgs_dir}")

        valid_ext = (".png", ".jpg", ".jpeg", ".webp")
        images = [
            os.path.join(slide_imgs_dir, f)
            for f in os.listdir(slide_imgs_dir)
            if f.lower().endswith(valid_ext)
        ]

        if not images:
            raise ValueError(f"No slide images found in: {slide_imgs_dir}")

        images.sort(key=self._extract_slide_number)
        return images

    def _clean_json_text(self, text: str) -> str:
        """
        Clean model output and isolate JSON if extra text appears.
        """
        text = text.strip()

        # Remove markdown fences if model adds them
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        # Isolate JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

        return text.strip()

    def _normalize_focus_text(self, focus: str) -> str:
        """
        Light cleanup for weak/generic focus prompts.
        """
        focus = focus.strip()

        replacements = {
            "first bullet point": "bullet text being explained",
            "second bullet point": "bullet text being explained",
            "third bullet point": "bullet text being explained",
            "the slide title": "main title text",
            "the diagram": "relevant diagram region being discussed",
            "the chart": "relevant chart region being discussed",
            "left side": "relevant content on the left being discussed",
            "right side": "relevant content on the right being discussed",
            "this section": "exact text or visual area being discussed",
            "important part": "exact text or visual area being discussed",
        }

        lower_focus = focus.lower()
        for bad, better in replacements.items():
            if lower_focus == bad:
                return better

        return focus

    def _safe_parse_response(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse model response safely.
        Expected format:
        {
          "sentences": [
            {"sentence": "...", "focus": "..."}
          ]
        }
        """
        cleaned = self._clean_json_text(raw_text)

        try:
            data = json.loads(cleaned)

            if "sentences" not in data or not isinstance(data["sentences"], list):
                raise ValueError("Missing 'sentences' list")

            validated = []
            for item in data["sentences"]:
                if not isinstance(item, dict):
                    continue

                sentence = str(item.get("sentence", "")).strip()
                focus = str(item.get("focus", "")).strip()
                focus = self._normalize_focus_text(focus)

                if sentence and focus:
                    validated.append({
                        "sentence": sentence,
                        "focus": focus
                    })

            if not validated:
                raise ValueError("No valid sentence-focus pairs found")

            return {"sentences": validated}

        except Exception:
            return self._fallback_from_text(raw_text)

    def _fallback_from_text(self, raw_text: str) -> Dict[str, Any]:
        """
        Fallback parser if the model returns invalid JSON.
        Tries to recover from formats like:
            sentence | focus
            sentence - focus
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        extracted = []

        for line in lines:
            parts = None

            if "|" in line:
                parts = line.split("|", 1)
            elif " - " in line:
                parts = line.split(" - ", 1)

            if not parts or len(parts) != 2:
                continue

            sentence = parts[0].strip()
            focus = self._normalize_focus_text(parts[1].strip())

            if sentence and focus:
                extracted.append({
                    "sentence": sentence,
                    "focus": focus
                })

        if not extracted:
            extracted = [{
                "sentence": "This slide presents the main idea shown on the screen.",
                "focus": "main title and central slide content"
            }]

        return {"sentences": extracted}

    def _build_user_prompt(self, slide_index: int) -> str:
        return (
            f"This is slide {slide_index}.\n"
            "Analyze the slide image carefully.\n"
            "Generate a natural presenter-style spoken script for this slide.\n"
            "For each spoken sentence, generate one highly specific cursor focus prompt.\n"
            "Return only valid JSON using the required structure."
        )

    def process_single_slide(self, image_path: str, slide_index: int) -> Dict[str, Any]:
        print(f"Processing slide {slide_index}: {image_path}")

        response = self.client.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": self._build_user_prompt(slide_index),
                    "images": [image_path]
                }
            ]
        )

        raw_text = response["message"]["content"]
        parsed = self._safe_parse_response(raw_text)

        return {
            "slide_number": slide_index,
            "image_path": image_path,
            "content": parsed["sentences"]
        }

    def run(self, slide_imgs_dir: str) -> Dict[str, Any]:
        slide_images = self.get_slide_images(slide_imgs_dir)

        results: Dict[str, Any] = {}

        for idx, image_path in enumerate(slide_images, start=1):
            slide_result = self.process_single_slide(image_path, idx)

            results[f"slide_{idx}"] = {
                "image": slide_result["image_path"],
                "items": slide_result["content"]
            }

        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\nSaved subtitle output to: {self.output_path}")
        return results


if __name__ == "__main__":
    slide_images_dir = "Data/intermediate/lecture1_slides"
    output_file = "Data/output/subtitles.json"

    agent = SubtitleCursorAgent(
        model_name="qwen2.5vl:7b",
        output_path=output_file
    )

    agent.run(slide_images_dir)
