# Agents/summary_agent.py



import os
import fitz
import ollama

from Prompts.summary_prompt import SUMMARY_PROMPT

def _extract_pdf_text(
    pdf_path: str,
    base_data_dir: str = "Data",
    max_pages: int | None = None,
) -> str:

    doc = fitz.open(pdf_path)

    total_pages = len(doc)
    n = total_pages if max_pages is None else min(total_pages, max_pages)

    full_text = ""

    for i in range(n):
        page_text = doc[i].get_text("text")
        full_text += f"\n\n===== PAGE {i+1} =====\n\n"
        if page_text:
            full_text += page_text

    doc.close()

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    intermediate_dir = os.path.join(base_data_dir, "intermediate")
    os.makedirs(intermediate_dir, exist_ok=True)

    extracted_path = os.path.join(
        intermediate_dir,
        f"{pdf_name}_extracted.txt"
    )

    with open(extracted_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"Extracted text saved to: {extracted_path}")

    return full_text


def summarize_pdf_to_text(
    pdf_path: str,
    model_name: str,
    output_txt_path: str | None = None,
    base_data_dir: str = "Data",
    max_pages: int | None = None,
) -> str:

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

    if output_txt_path is None:
        out_dir = os.path.join(base_data_dir, "output")
        os.makedirs(out_dir, exist_ok=True)
        output_txt_path = os.path.join(out_dir, f"{pdf_name}_summary.txt")
    else:
        os.makedirs(os.path.dirname(output_txt_path) or ".", exist_ok=True)

    doc_text = _extract_pdf_text(pdf_path, base_data_dir=base_data_dir, max_pages=max_pages)

    response = ollama.chat(
        model=model_name,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": f"doc_text:\n{doc_text}"},
        ],
    )

    summary_text = response["message"]["content"].strip()

    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    return output_txt_path