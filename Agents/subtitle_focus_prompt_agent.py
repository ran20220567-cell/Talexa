
import os
import re
import ollama

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Prompts.subtitle_cursor_prompt import SUBTITLE_CURSOR_PROMPT


class SubtitleCursorAgent:

    def __init__(self, model_name="qwen2.5vl:7b"):
        self.model_name = model_name

    def get_slide_images(self, slide_imgs_dir):

        if not os.path.exists(slide_imgs_dir):
            raise FileNotFoundError(f"Slide image folder not found: {slide_imgs_dir}")

        valid_ext = (".png", ".jpg", ".jpeg", ".webp")

        images = [
            os.path.join(slide_imgs_dir, f)
            for f in os.listdir(slide_imgs_dir)
            if f.lower().endswith(valid_ext)
        ]

        def extract_number(path_str):
            nums = re.findall(r"\d+", os.path.basename(path_str))
            return int(nums[-1]) if nums else 0

        images.sort(key=extract_number)

        return images

    def generate_script(self, image_path, slide_idx):

        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": SUBTITLE_CURSOR_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Generate the presentation script for slide {slide_idx}.",
                    "images": [image_path]
                }
            ],
            options={
                "temperature": 0.2,
                "num_predict": 512
            }
        )

        text = response["message"]["content"].strip()

        # remove markdown if model adds it
        text = text.replace("```", "").strip()

        return text

    def run(self, slide_imgs_dir, output_path=None):

        slide_images = self.get_slide_images(slide_imgs_dir)

        if output_path is None:
            output_path = "Data/output/slide_script_cursor.txt"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        all_slides_output = []

        for idx, image_path in enumerate(slide_images, start=1):

            print(f"Processing slide {idx}/{len(slide_images)}")

            try:
                slide_script = self.generate_script(image_path, idx)
            except Exception as e:
                print(f"Error on slide {idx}: {e}")
                slide_script = "This slide presents the main idea | title"

            all_slides_output.append(slide_script)

        final_output = "\n###\n".join(all_slides_output)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_output)

        print(f"Subtitle script saved to: {output_path}")

        return output_path


if __name__ == "__main__":

    agent = SubtitleCursorAgent(model_name="qwen2.5vl:7b")

    result = agent.run(
        slide_imgs_dir=r"Data\intermediate\lecture1_slides"
    )

    print("Result file:", result)
