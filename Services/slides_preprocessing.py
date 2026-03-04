import os
import re
import fitz

PREPARED_RE = re.compile(r"^Prepared by\b", re.IGNORECASE)
FOOTER_PAGE_RE = re.compile(r"(www\.psut|Call:|Fax:|Email:|psut\.edu\.jo|Princess Sumaya)", re.IGNORECASE)

def pdf_slides_to_markdown(pdf_path):
    doc = fitz.open(pdf_path)
    md_lines = []

    for page in doc:
        text = page.get_text("text") or ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            continue

        # skip pages that are basically just contact/footer page
        joined = " ".join(lines)
        if FOOTER_PAGE_RE.search(joined) and len(lines) <= 12:
            continue

        # remove page number-only lines
        lines = [l for l in lines if not l.isdigit()]
        if not lines:
            continue

        # remove "Prepared by ..." if it's the first line
        if lines and PREPARED_RE.match(lines[0]):
            lines = lines[1:]
        if not lines:
            continue

        # heading = first remaining line
        title = lines[0]
        content = lines[1:]

        # if no content under heading, skip (usually image-only slides)
        if not content:
            continue

        md_lines.append("# " + title)
        md_lines.extend(content)
        md_lines.append("")

    doc.close()

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_dir = r"C:\Users\user\Desktop\Talexa\Data\intermediate"
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"{pdf_name}_markdown.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines).strip() + "\n")

    return out_path