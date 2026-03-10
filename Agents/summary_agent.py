# Agents/summary_agent.py

import os
import re
import fitz
import ollama

from Prompts.summary_prompt import SUMMARY_PROMPT


class SummaryAgent:

    def __init__(self, model_name="qwen2.5:7b", base_data_dir="Data"):
        self.model_name = model_name
        self.base_data_dir = base_data_dir

    def extract_pdf_text(self, pdf_path, max_pages=None):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

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
        intermediate_dir = os.path.join(self.base_data_dir, "intermediate")
        os.makedirs(intermediate_dir, exist_ok=True)

        extracted_path = os.path.join(
            intermediate_dir,
            f"{pdf_name}_extracted.txt"
        )

        with open(extracted_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        print(f"Extracted text saved to: {extracted_path}")

        return full_text


    def split_by_sections(self, text):
       

        pattern = r'(?m)^\s*(\d+(?:\.\d+)+)\s+(.+?)\s*$'
        matches = list(re.finditer(pattern, text))

        print("\nDetected section headings:")
        for i, m in enumerate(matches, 1):
            print(f"{i}. {m.group(1)} {m.group(2)}")

        if not matches:
            return [text.strip()]

        sections = []

        first_start = matches[0].start()
        intro = text[:first_start].strip()
        if intro:
            sections.append(intro)

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()
            if section_text:
                sections.append(section_text)

        
        return sections


    def generate_summary(self, doc_text):
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Rewrite and condense this academic text while keeping about 50–60% "
                        "of the information. Do not over-shorten it. Keep the important "
                        "definitions, explanations, and examples.\n\n"
                        f"{doc_text}"
                    )
                },
            ],
        )
        summary_text = response["message"]["content"].strip()
        return summary_text


    def summarize_sections(self, doc_text):
        sections = self.split_by_sections(doc_text)
        summaries = []

        print(f"Detected {len(sections)} section blocks.")

        for i, section in enumerate(sections, 1):
            print(f"Summarizing section {i}/{len(sections)}...")
            section_summary = self.generate_summary(section)
            summaries.append(section_summary)

        return "\n\n".join(summaries)


    def save_summary(self, summary_text, output_txt_path):
        os.makedirs(os.path.dirname(output_txt_path) or ".", exist_ok=True)

        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(summary_text)

        print(f"Summary saved to: {output_txt_path}")


    def run(self, pdf_path, output_txt_path=None, max_pages=None):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

        if output_txt_path is None:
            out_dir = os.path.join(self.base_data_dir, "output")
            os.makedirs(out_dir, exist_ok=True)
            output_txt_path = os.path.join(out_dir, f"{pdf_name}_summary.txt")
        else:
            os.makedirs(os.path.dirname(output_txt_path) or ".", exist_ok=True)

        doc_text = self.extract_pdf_text(pdf_path, max_pages=max_pages)
        summary_text = self.summarize_sections(doc_text)
        self.save_summary(summary_text, output_txt_path)

        print("Summary agent completed successfully.")
        return output_txt_path


if __name__ == "__main__":
    agent = SummaryAgent(model_name="qwen2.5:7b")

    result_path = agent.run(
        pdf_path=r"Data/input/slides/AI_ch1.pdf",
        output_txt_path=r"C:\Users\user\Desktop\Talexa\Data\output\AI_ch2_summary.txt",
        max_pages=None
    )

    print(f"\nFinal summary file: {result_path}")
