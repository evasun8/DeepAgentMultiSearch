import markdown
from weasyprint import HTML
from pathlib import Path
import logging

def convert_md_to_pdf_via_word(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """
    Converts a Markdown document to a formatted PDF using WeasyPrint.
    This approach correctly parses Markdown syntax into HTML/CSS before rendering.
    """
    try:
        # 1. Read the Markdown content
        with open(md_abs_path, 'r', encoding='utf-8') as f:
            md_text = f.read()

        # 2. Parse Markdown to HTML (including support for tables and code blocks)
        html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

        # 3. Inject CSS to ensure proper rendering of headers, tables, and spacing
        full_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: sans-serif; padding: 40px; line-height: 1.6; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 4px; font-family: monospace; }}
            </style>
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """

        # 4. Render HTML to PDF
        HTML(string=full_html).write_pdf(str(pdf_abs_path))
        
        if pdf_abs_path.exists():
            return f"Conversion successful: {pdf_abs_path}"
        else:
            return "Conversion failed: PDF file was not created."

    except Exception as e:
        logging.error(f"Conversion failed: {e}", exc_info=True)
        return f"Conversion failed: {str(e)}"