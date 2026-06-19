import logging
from pathlib import Path
from typing import Annotated, Optional

from langchain_core.tools import tool
from api.monitor import monitor
from api.context import get_session_context
from utils.path_utils import resolve_path

# Attempt to import optional dependencies for on-demand loading
try:
    import docx
except ImportError:
    docx = None
    
try:
    import pypdf
except ImportError:
    pypdf = None
    
try:
    import pandas as pd
except ImportError:
    pd = None
    
@tool
def read_file_content(
        filename: Annotated[str, "Name or path of the file to read (supports .md, .docx, .pdf, .xlsx, .xls)"],
        instruction: Annotated[str, "Specific instructions for content extraction (e.g., 'summarize', 'analyze data')"] = "Extract full content"
) -> str:
    """
    Read the content of a specified file. Supports Markdown (.md), Word (.docx), PDF (.pdf), and Excel (.xlsx/.xls).
    For Excel files, it automatically provides data statistics (head and describe).
    """
    
    monitor.report_tool(
        tool_name="read_file_content",
        args={"filename": filename, "instruction": instruction},
    )
    
    # ====================== 1. Path Resolution ======================
    session_dir = get_session_context()
    file_path = resolve_path(filename, session_dir)
    
    if not file_path.exists():
        return f"File not found: {file_path}"
    
    ext = file_path.suffix.lower()
    
    try:
        if ext in [".md", ".txt"]:
            return file_path.read_text(encoding="utf-8")
        elif ext == ".docx":
            if docx is None:
                return "Error: 'python-docx' library is not installed; cannot read Word files."
            doc = docx.Document(file_path)
            full_text = [para.text for para in doc.paragraphs]
            return "\n".join(full_text)
        elif ext == ".pdf":
            if pypdf is None:
                return "Error: 'pypdf' library is not installed; cannot read PDF files."
            pdf_reader = pypdf.PdfReader(file_path)
            text = "\n".join([page.extract_text() for page in pdf_reader.pages])
            return text
        elif ext in [".xlsx", ".xls"]:
            if pd is None:
                return "Error: 'pandas' library is not installed; cannot read Excel files."
            try:
                df = pd.read_excel(str(file_path))
            except Exception as e:
                return f"Error: {str(e)}"
            
            result = [
                f"Filename: {filename}",
                f"Rows: {len(df)}, Columns: {len(df.columns)}",
                f"Columns names: {', '.join(df.columns)}",
                "\n[First 5 rows preview]:",
                df.head().to_string(index=False),
                "\n[Statistical description]:",
                df.describe().to_string()
            ]
            return "\n".join(result)
        else:
            try:
                return file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                return f"Error: Unsupported file format '{ext}' and could not be read as plain text."

    except Exception as e:
        return f"Error reading file: {str(e)}"