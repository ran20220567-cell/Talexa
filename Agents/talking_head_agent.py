import os
import glob
import shutil
import subprocess
from pathlib import Path


class TalkingHeadAgent:
    def __init__(
        self,
        source_image="Data/input/portrait.png",
        speech_dir="Data/output/speech/lecture1",
        output_dir="Data/output/talking_head/lecture1",
        hallo_root="/workspace/hallo2",
        hallo_python="/workspace/hallo2/env/bin/python",
        config_template="/workspace/hallo2/configs/inference/long.yaml",
        script_path="/workspace/hallo2/scripts/inference_long.py",
        gpu_id=0,
    ):
        self.source_image = os.path.abspath(source_image)
        self.speech_dir = os.path.abspath(speech_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.hallo_root = os.path.abspath(hallo_root)
        self.hallo_python = os.path.abspath(hallo_python)
        self.config_template = os.path.abspath(config_template)
        self.script_path = os.path.abspath(script_path)
        self.gpu_id = str(gpu_id)

        os.makedirs(self.output_dir, exist_ok=True)

    def get_audio_files(self):
        return sorted(glob.glob(os.path.join(self.speech_dir, "slide_*.wav")))

    def make_config_for_slide(self, slide_dir):
        config_out = os.path.join(slide_dir, "long.yaml")

        with open(self.config_template, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated = []

        for line in lines:
            stripped = line.strip()
            indent = line[: len(line) - len(line.lstrip())]

            if stripped.startswith("save_path:"):
                updated.append(f"{indent}save_path: {slide_dir}\n")
            else:
                updated.append(line)

        with open(config_out, "w", encoding="utf-8") as f:
            f.writelines(updated)

        return config_out

    def merge_audio_video(self, video_path, audio_path, output_path):
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd, check=True)

    def run_one(self, audio_path):
        slide_name = Path(audio_path).stem
        slide_dir = os.path.join(self.output_dir, slide_name)
        os.makedirs(slide_dir, exist_ok=True)

        config_path = self.make_config_for_slide(slide_dir)

        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = self.gpu_id

        cmd = [
            self.hallo_python,
            self.script_path,
            "--config",
            config_path,
            "--source_image",
            self.source_image,
            "--driving_audio",
            audio_path,
        ]

        subprocess.run(cmd, cwd=self.hallo_root, env=env, check=True)

        candidates = [
            os.path.join(slide_dir, "portrait", "merge_video.mp4"),
            os.path.join(slide_dir, "merge_video.mp4"),
            os.path.join(self.hallo_root, "output_long", "debug", "1", "merge_video.mp4"),
        ]

        merge_video = None
        for path in candidates:
            if os.path.exists(path):
                merge_video = path
                break

        if merge_video is None:
            raise FileNotFoundError(f"merge_video.mp4 not found for {slide_name}")

        final_video = os.path.join(self.output_dir, f"{slide_name}.mp4")
        self.merge_audio_video(merge_video, audio_path, final_video)

        print(f"[TalkingHead] Saved: {final_video}")

    def run(self, limit_slides=None):
        if not os.path.exists(self.source_image):
            raise FileNotFoundError(f"Source image not found: {self.source_image}")

        if not os.path.isdir(self.speech_dir):
            raise FileNotFoundError(f"Speech directory not found: {self.speech_dir}")

        audio_files = self.get_audio_files()

        if not audio_files:
            raise FileNotFoundError(f"No slide wav files found in: {self.speech_dir}")

        if limit_slides is not None:
            audio_files = audio_files[:limit_slides]

        print(f"[TalkingHead] Slides to process: {len(audio_files)}")

        for audio_path in audio_files:
            print(f"[TalkingHead] Processing: {os.path.basename(audio_path)}")
            self.run_one(audio_path)

        print("[TalkingHead] All done.")


if __name__ == "__main__":
    agent = TalkingHeadAgent(
        source_image="Data/input/portrait.png",
        speech_dir="Data/output/speech/lecture1",
        output_dir="Data/output/talking_head/lecture1",
        hallo_root="/workspace/hallo2",
        hallo_python="/workspace/hallo2/env/bin/python",
        config_template="/workspace/hallo2/configs/inference/long.yaml",
        script_path="/workspace/hallo2/scripts/inference_long.py",
        gpu_id=0,
    )
    agent.run()
