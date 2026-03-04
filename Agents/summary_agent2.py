import argparse
from pathlib import Path

import fitz
from ollama import chat as ollama_chat


def extract_text_fast(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    parts = []
    for i in range(len(doc)):
        parts.append(doc[i].get_text("text") or "")
    return "\n".join(parts).strip()


def chunk_text(text: str, chunk_size: int = 6000, overlap: int = 600) -> list[str]:
    chunks = []
    i = 0
    step = max(1, chunk_size - overlap)
    while i < len(text):
        chunks.append(text[i : i + chunk_size])
        i += step
    return chunks


def load_prompt(prompts_dir: Path) -> str:
    p = prompts_dir / "summary_prompt.txt"
    if not p.exists():
        raise FileNotFoundError(f"Missing prompt: {p}")
    return p.read_text(encoding="utf-8").strip()


def vlm_summarize_text(model: str, system_prompt: str, user_text: str) -> str:
    resp = ollama_chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )
    msg = getattr(resp, "message", None)
    return (getattr(msg, "content", "") or "").strip()


def ensure_not_too_short(model: str, system_prompt: str, summary_text: str) -> str:
    min_words = 220
    if len(summary_text.split()) >= min_words:
        return summary_text.strip()

    expand_instruction = (
        "The summary below is too short for academic slides.\n"
        "Rewrite it with MORE detail but do NOT add any new facts.\n"
        "Keep the same structure: TITLE then 4–6 subtitles.\n"
        "Each subtitle: 4–6 bullets. Each bullet: 10–18 words.\n"
        "Do NOT mention images/figures/tables unless explained in the text.\n"
        "Do NOT ask questions. Do NOT add extra sections.\n\n"
        "SUMMARY TO EXPAND:\n"
        f"{summary_text}\n"
    )
    expanded = vlm_summarize_text(model, system_prompt, expand_instruction)
    return expanded if expanded else summary_text.strip()


def run_summary_agent(base_dir: Path, pdf_filename: str, model: str = "qwen2.5vl:7b") -> Path:
    data_dir = base_dir / "Data"
    prompts_dir = base_dir / "Prompts"
    intermediate_dir = data_dir / "intermediate"
    output_dir = data_dir / "output"
    input_dir = data_dir / "input"

    intermediate_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = input_dir / pdf_filename
    if not pdf_path.exists():
        raise FileNotFoundError(f"Put the PDF here: {pdf_path}")

    prompt = load_prompt(prompts_dir)

    text = extract_text_fast(pdf_path)
    (intermediate_dir / "extracted_text.txt").write_text(text, encoding="utf-8")

    if not text.strip():
        raise ValueError(
            "No selectable text extracted. This PDF might be scanned.\n"
            "If it's scanned, you need OCR (or a vision-per-page approach)."
        )

    chunks = chunk_text(text, chunk_size=6000, overlap=600)
    chunk_summaries = []

    for idx, chunk in enumerate(chunks, start=1):
        print(f"[VLM] Summarizing chunk {idx}/{len(chunks)}...")
        s = vlm_summarize_text(model, prompt, chunk)
        if s:
            chunk_summaries.append(s)

    (intermediate_dir / "chunk_summaries.txt").write_text("\n\n".join(chunk_summaries), encoding="utf-8")

    if not chunk_summaries:
        raise ValueError("Chunk summaries are empty. The model returned no output.")

    merge_instruction = (
        "You will receive multiple chunk summaries.\n"
        "Merge them into ONE clean final summary following EXACTLY the required output format.\n"
        "Do NOT repeat points. Remove duplicates. Keep it slide-friendly.\n"
        "Do NOT add new information.\n\n"
        "CHUNK SUMMARIES:\n"
        + "\n\n".join(chunk_summaries)
    )

    final = vlm_summarize_text(model, prompt, merge_instruction)
    final = ensure_not_too_short(model, prompt, final)

    out_path = output_dir / "summary_output.txt"
    out_path.write_text(final, encoding="utf-8")
    print(f"Saved -> {out_path}")
    return out_path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", required=True, help="PDF filename inside Data/input/")
    p.add_argument("--model", default="qwen2.5vl:7b", help="Ollama model name")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    base_dir = Path(__file__).resolve().parent.parent
    run_summary_agent(base_dir, args.pdf, model=args.model)
