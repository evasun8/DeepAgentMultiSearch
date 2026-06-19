import logging
import sys
from pathlib import Path

try:
    from typing import Annotated, Optional
except ImportError:
    from typing_extensions import Annotated, Optional

from langchain_core.tools import tool
from api.monitor import monitor
from api.context import get_session_context
from utils.path_utils import resolve_path
from utils.word_converter import convert_md_to_pdf_via_word


@tool
def convert_md_to_pdf(
        md_filename: Annotated[str, "The path of the Markdown document to convert (including .md extension)"],
        pdf_filename: Annotated[Optional[str], "The output PDF file path (optional, defaults to the same name as the source)"] = None
) -> str:
    """
    Converts a Markdown document to PDF (using a word engine).
    Optimization: Separates path/resource management logic, keeping the Tool layer focused on orchestration.
    """
    monitor.report_tool("Markdown to PDF Tool")

    try:
        # 1. Path preprocessing
        session_dir = get_session_context()
        md_path = Path(md_filename).with_suffix('.md')
        md_abs_path = Path(resolve_path(str(md_path), session_dir))

        # 2. Check if source file exists
        if not md_abs_path.exists():
            return f"Error: File does not exist {md_abs_path}"

        # 3. Determine output path
        if pdf_filename:
            pdf_path = Path(pdf_filename).with_suffix('.pdf')
            pdf_abs_path = Path(resolve_path(str(pdf_path), session_dir))
        else:
            pdf_abs_path = md_abs_path.with_suffix('.pdf')

        # 4. Invoke core conversion logic
        return convert_md_to_pdf_via_word(md_abs_path, pdf_abs_path)

    except Exception as e:
        logging.error(f"Conversion failed: {e}", exc_info=True)
        return f"Conversion failed: {str(e)}"


if __name__ == '__main__':
    # Test block
    # Override get_session_context for testing purposes
    get_session_context = lambda: "./test_session_123"

    # Create test directory and file
    Path("./test_session_123/sub_dir").mkdir(parents=True, exist_ok=True)
    with open("./test_session_123/sub_dir/test_file.md", "w", encoding="utf-8") as f:
        f.write("# Title\n\nTest content\n\n|A|B|\n|---|---|\n|1|2|")

    print(convert_md_to_pdf.invoke({"md_filename": "sub_dir/test_file.md"}))
    