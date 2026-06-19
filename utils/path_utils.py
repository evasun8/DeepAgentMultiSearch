import os
from pathlib import Path
from typing import Optional

def resolve_path(filename: str, session_dir: Optional[str] = None) -> str:
    """
    Unified file path resolution utility.

    Core Functions:
    1. Cleans virtual path prefixes (/workspace, /mnt/data, /home/user)
    2. Identifies 'updated/' directory, prioritizing resolution relative to the CWD (Current Working Directory).
    3. Merges paths with session_dir to guarantee sandbox path isolation.
    4. Prevents path nesting issues (e.g., session_id/session_id).

    Scenarios & Examples (Based on macOS Test Env: session_dir=/Users/user/Project/output/session_123, CWD=/Users/user/Project):

    | Input Scenario             | filename                                              | session_dir                         | Core Operation                         | Final Output Result                            |
    |----------------------------|-------------------------------------------------------|-------------------------------------|----------------------------------------|------------------------------------------------|
    | Virtual Path Cleanup       | /workspace/report.md                                  | /Users/user/Project/output/session_123| Strips /workspace → appends to session  | /Users/user/Project/output/session_123/report.md|
    | 'updated/' Processing      | abc/updated/upload/file.pdf                           | /Users/user/Project/output/session_123| Extracts 'updated/' path → CWD relative | /Users/user/Project/updated/upload/file.pdf   |
    | No Session Directory       | sub/test.md                                           | None                                | Resolves directly relative to CWD      | /Users/user/Project/sub/test.md               |
    | Absolute Path (In Session) | /Users/user/Project/output/session_123/sub/report.md  | /Users/user/Project/output/session_123| Verified inside session → returns as-is| /Users/user/Project/output/session_123/sub/report.md|
    | Absolute Path (Out Session)| /Users/other/file.md                                  | /Users/user/Project/output/session_123| Verified outside session → keeps origin | /Users/other/file.md                           |
    | Path Nesting Protection    | /Users/user/Project/output/session_123/session_123/a.md| /Users/user/Project/output/session_123| Detects duplicate session_123 → repairs| /Users/user/Project/output/session_123/a.md     |
    | Relative Path (w/ Session) | session_123/report.md                                 | /Users/user/Project/output/session_123| Matches session name → prevents nesting| /Users/user/Project/output/session_123/report.md|
    | Relative Path (w/ Output)  | output/report.md                                      | /Users/user/Project/output/session_123| Matches output prefix → standardizes    | /Users/user/Project/output/session_123/report.md|
    | Standard Relative Path     | sub1/sub2/test.md                                     | /Users/user/Project/output/session_123| No special flags → appends to session  | /Users/user/Project/output/session_123/sub1/sub2/test.md|
    | Virtual Path + 'updated'    | /mnt/data/updated/doc.md                              | /Users/user/Project/output/session_123| Strips /mnt/data → triggers updated/ rule| /Users/user/Project/updated/doc.md             |

    Args:
        filename (str): The incoming raw string filename or path.
        session_dir (str, optional): The sandbox session context folder directory.

    Returns:
        str: The fully resolved absolute target path string.
    """
    path = Path(filename)
    path_str = filename.replace("\\", "/")  # Standardize all separators for cross-platform string matching

    # 1. Virtual Path Cleanup
    virtual_prefixes = ["/workspace", "/mnt/data", "/home/user"]
    for prefix in virtual_prefixes:
        if path_str.startswith(prefix):
            cleaned = path_str[len(prefix):].lstrip("/")
            path = Path(cleaned)
            path_str = str(path).replace("\\", "/")
            break

    # 2. Special Processing: updated/ (User Upload Directory)
    # Whenever a path contains 'updated/', extract its trailing portion and resolve relative to CWD.
    if "updated/" in path_str:
        idx = path_str.find("updated/")
        relative_part = path_str[idx:]
        return str(Path(relative_part).resolve())

    if not session_dir:
        return str(path.resolve())

    session_path = Path(session_dir).resolve()
    session_name = session_path.name

    # 3. Merging Path with Session Context
    is_unix_abs = path_str.startswith("/")

    # If it is an absolute path (Windows drive letters or Unix forward slashes)
    if path.is_absolute() or (os.name == 'nt' and is_unix_abs):
        # Windows-specific edge case: starts with / but missing drive letter is handled as relative
        if os.name == 'nt' and is_unix_abs and not path.drive:
            full_path = session_path / path_str.lstrip("/")
        else:
            full_path = path.resolve()

        # Check whether the absolute path falls inside the sandbox session directory
        try:
            if session_path in full_path.parents or full_path == session_path:
                # Anti-Nesting Protection (e.g., .../session_abc/session_abc/file.txt)
                parts = full_path.parts
                for i in range(len(parts) - 1):
                    if parts[i] == session_name and parts[i + 1] == session_name:
                        # Nesting issue found, fall back to safe structural reconstruction
                        return str(session_path / full_path.name)
                return str(full_path)
        except Exception:
            pass

        # Absolute path but verified outside session_dir -> return as-is
        return str(full_path)
        
    else:
        # Relative Path Processing
        parts = path.parts

        # Prevent duplicate nested session attachments
        if session_name in parts:
            return str(session_path / path.name)
        if parts and parts[0] == "output":
            return str(session_path / path.name)

        # Default fallback behavior: append directly to session workspace
        return str(session_path / path)
