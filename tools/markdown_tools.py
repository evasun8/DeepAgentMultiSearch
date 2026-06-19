import logging
from pathlib import Path

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

from langchain_core.tools import tool
from api.monitor import monitor
from api.context import get_session_context
from utils.path_utils import resolve_path

# Markdown Generation Tool
@tool
def generate_markdown(
        content: Annotated[str, "The text content to be written into the Markdown document"],
        filename: Annotated[str, "The filename of the Markdown document (with or without .md extension)"],
        path: Annotated[str, "The relative path where the file should be saved"] = ""
):
    """Generates a Markdown (.md) file based on the provided text content."""
    
    print(f"Path is: {path}")
    monitor.report_tool("Markdown Generation Tool", {"content_length": len(content)})
    
    if not filename.endswith('.md'):
        filename += '.md'

    # Get the session directory from context
    session_dir = get_session_context()
    print(f"⚠️ session_dir retrieved in generate_markdown: {session_dir}")

    # --- Path Cleaning and Redirection Logic ---
    # Combine path and filename
    if path and path != ".":
        full_input_path = str(Path(path) / filename)
    else:
        full_input_path = filename
    
    full_path_str = resolve_path(full_input_path, session_dir)
    file_path = Path(full_path_str)

    # Get parent directory
    parent_dir = file_path.parent

    print(f"[MarkdownTool] Debug: parent_dir={parent_dir}, filename={filename}, full_path={file_path}")

    try:
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)
            print(f"[MarkdownTool] Created directory: {parent_dir}")

        # Write text directly using Path
        file_path.write_text(content, encoding='utf-8')

        print(f"[MarkdownTool] Successfully wrote to: {file_path}")
        return f"Markdown file '{file_path}' has been successfully generated and saved."
    except Exception as e:
        print(f"[MarkdownTool] Error writing file: {e}")
        return f"Failed to generate Markdown file: {str(e)}"


# -------------------------- Test Code --------------------------
if __name__ == "__main__":
    # ========== Core: Override get_session_context for testing ==========
    def get_session_context():
        """Test-only: Provides a fixed initialization value for session_dir."""
        return "./test_session_123"

    # ========== Test logic ==========
    test_content = "# Test Document\nThis is content written after fixing the session_dir."
    test_filename = "test_file"  # No .md extension, testing auto-completion
    test_path = "sub_dir"        # Relative path

    # Call the generation function
    print("===== Starting test (session_dir set to: ./test_session_123) =====")
    result = generate_markdown.invoke({
        "content": test_content,
        "filename": test_filename,
        "path": test_path
    })

    # Verify results
    print(f"\nResult: {result}")
    if "successfully generated" in result:
        file_path = Path(result.split("'")[1])
        print(f"✅ Verification: File {file_path} {'exists' if file_path.exists() else 'does not exist'}")