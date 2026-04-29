import os
import json
import time
import re
import base64
from pathlib import Path
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBEFTz4OnAbuRXq4ZnGXQXUpfkx9VJThU0")
if not API_KEY:
    raise EnvironmentError("Missing GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]

RETRY_429_DELAY = 15
MAX_429_RETRIES = 3

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

VIDEO_MIME_MAP = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
}


class PresentQuizEvaluator:

    def __init__(self, model_name="gemini-2.5-flash", num_questions=4):
        self.model_id = model_name
        self.num_questions = num_questions

    def load_slide_images(self, slides_dir):
        folder = Path(slides_dir)

        images = sorted(
            f for f in folder.iterdir()
            if f.suffix.lower() in IMAGE_EXTENSIONS
        )

        parts = []
        for img in images:
            mime = MIME_MAP[img.suffix.lower()]
            data = base64.b64encode(img.read_bytes()).decode("utf-8")

            parts.append(
                types.Part(
                    inline_data=types.Blob(mime_type=mime, data=data)
                )
            )

        return parts

    def load_video(self, video_path):
        path = Path(video_path)
        mime = VIDEO_MIME_MAP[path.suffix.lower()]
        data = base64.b64encode(path.read_bytes()).decode("utf-8")

        return types.Part(
            inline_data=types.Blob(mime_type=mime, data=data)
        )

    def _parse_json(self, text):
        text = re.sub(r"^```(json)?", "", text.strip())
        text = re.sub(r"```$", "", text.strip())
        return json.loads(text)

    def _call_model(self, model, contents, config):
        for _ in range(MAX_429_RETRIES):
            try:
                res = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                if res.text:
                    return self._parse_json(res.text)
            except Exception as e:
                if "429" in str(e):
                    time.sleep(RETRY_429_DELAY)
                    continue
        return None

    def _try_models(self, contents, config, label):
        for m in [self.model_id] + MODELS_TO_TRY:
            print(f"[{label}] using {m}")
            try:
                out = self._call_model(m, contents, config)
                if out:
                    return out
            except Exception:
                continue
        return None

    def generate_questions(self, media_parts):
        print("\n[Phase 1] Generating questions...")

        prompt = f"""
Generate {self.num_questions} factual questions ONLY from the provided slides/video.

Return JSON:
[
  {{
    "question": "...",
    "answer": "..."
  }}
]
"""

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )

        contents = [
            types.Content(
                role="user",
                parts=media_parts + [types.Part(text=prompt)]
            )
        ]

        return self._try_models(contents, config, "Q-Gen")

    def answer_questions(self, questions, media_parts):
        print("\n[Phase 2] Answering questions...")

        q_block = "\n".join(
            f"{i+1}. {q['question']}"
            for i, q in enumerate(questions)
        )

        prompt = f"""
Answer ONLY using the provided content.

QUESTIONS:
{q_block}

Return JSON:
[
  {{
    "question_number": 1,
    "answer": "..."
  }}
]
"""

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )

        contents = [
            types.Content(
                role="user",
                parts=media_parts + [types.Part(text=prompt)]
            )
        ]

        answers = self._try_models(contents, config, "Q-A")

        ans_map = {a["question_number"]: a["answer"] for a in answers}

        enriched = []
        for i, q in enumerate(questions):
            enriched.append({
                **q,
                "vlm_answer": ans_map.get(i + 1, "")
            })

        return enriched

    def grade(self, qa_pairs):
        print("\n[Phase 3] Grading...")

        prompt_data = json.dumps([
            {
                "question": q["question"],
                "correct": q["answer"],
                "predicted": q["vlm_answer"]
            }
            for q in qa_pairs
        ], indent=2)

        prompt = f"""
Grade answers:

{prompt_data}

Return JSON:
[
  {{
    "question_number": 1,
    "score": 0.0-1.0
  }}
]
"""

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )

        contents = [
            types.Content(role="user", parts=[types.Part(text=prompt)])
        ]

        grades = self._try_models(contents, config, "Grade")

        gmap = {g["question_number"]: g["score"] for g in grades}

        for i, q in enumerate(qa_pairs):
            q["score"] = gmap.get(i + 1, 0.0)

        return qa_pairs


    def evaluate(self, slides_dir=None, video_path=None):

        if not slides_dir and not video_path:
            raise ValueError("Provide slides or video")

        if video_path:
            media_parts = [self.load_video(video_path)]
        else:
            media_parts = self.load_slide_images(slides_dir)

        questions = self.generate_questions(media_parts)
        qa = self.answer_questions(questions, media_parts)
        graded = self.grade(qa)

        total_score = sum(q["score"] for q in graded)
        max_score = self.num_questions  # e.g. 4

        os.makedirs("Evaluation/Results", exist_ok=True)

        output_path = "Evaluation/Results/present_quiz_result.json"

        result = {
            "total_score": total_score,
            "max_score": max_score,
            "questions": graded
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\nSaved to: {output_path}")
        print(f"Score: {total_score}/{max_score}")

        return result


if __name__ == "__main__":

    evaluator = PresentQuizEvaluator(
        model_name="gemini-2.5-flash",
        num_questions=4
    )

    evaluator.evaluate(
        slides_dir="Data/intermediate/slide_images",
        video_path="Data/output/ASSEMBLY_english_session3.mp4"
    )