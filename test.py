from Agents.summary_agent import summarize_pdf_to_text
import time


if __name__ == "__main__":

    pdf_path = "Data/input/AI_ch1.pdf"
    output_summary_path = None
    model_name = "qwen3-vl"

    print("Starting summary test...\n")

    start_time = time.time()   # ⏱ Start timer

    result_path = summarize_pdf_to_text(
        pdf_path=pdf_path,
        model_name=model_name,
        output_txt_path=output_summary_path,
        max_pages=None
    )

    end_time = time.time()  
    elapsed_time = end_time - start_time

    print("\nSummary saved to:", result_path)
    print("\nCheck extracted text in:")
    print("Data/intermediate/testpdf_extracted.txt")

    print(f"\nTotal Time : {elapsed_time:.2f} seconds")
    print("\nTest completed.")