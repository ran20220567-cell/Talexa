#this function is used to render PDFs to IMAGE needed for VLM

import os
from typing import List, Dict
import fitz  # PyMuPDF


def render_pdf_to_images(
    pdf_path: str,
    base_data_dir: str = "Data",
    dpi: int = 200,
    max_pages: int | None = None,
) -> List[Dict]:
    

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    renders_dir = os.path.join(
        base_data_dir,
        "intermediate",
        f"{pdf_name}_renders"
    )

    os.makedirs(renders_dir, exist_ok=True)

    doc = fitz.open(pdf_path)

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    total_pages = len(doc)
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    rendered_pages: List[Dict] = []

    for i in range(total_pages):
        page = doc[i]

        image_path = os.path.join(renders_dir, f"page_{i+1:04d}.png")

        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pix.save(image_path)

        rendered_pages.append({
            "page_index": i,
            "image_path": image_path,
        })

    doc.close()

    return rendered_pages