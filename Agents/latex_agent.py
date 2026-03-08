
import sys
import os
import subprocess
import ollama

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Prompts.latex_prompt import LATEX_PROMPT


class LatexAgent:

    def __init__(self, model="qwen2.5:7b"):
        self.model = model


    def escape_latex(self, text):

        replacements = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
        }

        for k, v in replacements.items():
            text = text.replace(k, v)

        return text


    def generate_latex(self, summary_path):

        if not os.path.exists(summary_path):
            raise FileNotFoundError(f"Summary file not found: {summary_path}")

        with open(summary_path, "r", encoding="utf-8") as f:
            summary_text = f.read()

        summary_text = self.escape_latex(summary_text)

        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": LATEX_PROMPT},
                {"role": "user", "content": f"summary_text:\n{summary_text}"}
            ]
        )

        latex_code = response["message"]["content"]
        latex_code = latex_code.replace("```latex", "").replace("```", "")

        return latex_code.strip()


    def save_latex(self, latex_code, output_path):

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(latex_code)

        print(f"LaTeX file saved at: {output_path}")


    def compile_pdf(self, tex_path):

        folder = os.path.dirname(tex_path)
        tex_file = os.path.basename(tex_path)

        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_file],
            cwd=folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode == 0:
            print("PDF compiled successfully.")
            return True
        else:
            print("LaTeX compilation failed.")
            return False


    def run(self, pdf_name, max_attempts=3):

        summary_path = f"Data/output/{pdf_name}_summary.txt"
        tex_output = f"Data/output/{pdf_name}.tex"

        attempt = 0

        while attempt < max_attempts:

            print(f"\nAttempt {attempt + 1} of {max_attempts}")

            latex_code = self.generate_latex(summary_path)

            self.save_latex(latex_code, tex_output)

            success = self.compile_pdf(tex_output)

            if success:
                print("Agent completed successfully.")
                return tex_output

            attempt += 1
            print("Retrying LaTeX generation...\n")

        print("Agent failed after multiple attempts.")
        return None

if __name__ == "__main__":
    agent = LatexAgent()
    agent.run("lecture1")