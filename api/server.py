import uuid
import asyncio
import uvicorn
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import shutil

# Add project root to sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent

# Import agent runner and monitor
# Note: Importing agent.main_agent initializes the agent, which may take a few seconds.
from agent.main_agent import run_deep_agent
from api.monitor import manager

app = FastAPI(title="DeepAgents API")

# Mount output directory so the frontend can access generated static files.
# Assumes the output directory is in the project root.
output_dir = project_root / "output"
output_dir.mkdir(exist_ok=True)

# Define the upload directory 'updated'
updated_dir = project_root / "updated"
updated_dir.mkdir(exist_ok=True)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TaskRequest(BaseModel):
    query: str
    thread_id: str = None

@app.on_event("startup")
async def startup_event():
    """
    On startup, retrieve the current event loop and bind it to the WebSocket manager.
    This ensures background threads can accurately post messages via run_coroutine_threadsafe.
    """
    loop = asyncio.get_running_loop()
    manager.set_loop(loop)
    print(f"[Server] WebSocket Manager bound to loop: {id(loop)}")

@app.post("/api/task")
async def run_task(request: TaskRequest):
    # 1. [ID Initialization]
    thread_id = request.thread_id or str(uuid.uuid4())

    # 2. [Background Execution] Run Agent asynchronously without blocking the main thread
    # Note: Using asyncio.create_task to trigger; the main_agent handles real-time push.
    asyncio.create_task(run_deep_agent(request.query, thread_id))

    # 3. [Immediate Response]
    return {"status": "started", "thread_id": thread_id}

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...), thread_id: str = Form(...)):
    """
    File Upload Interface.

    Goals:
    1. Receive one or more files uploaded by the user.
    2. Save them to the 'updated/session_{thread_id}' directory.
    3. Make them available for the Agent to read and analyze in subsequent tasks.
    """
    # 1. [Directory Prep] Ensure the upload directory exists
    target_dir = updated_dir / f"session_{thread_id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    # 2. [Save] Iterate and write files
    for file in files:
        file_path = target_dir / file.filename
        # Binary mode supports all formats (images, PDFs, text, etc.)
        # shutil.copyfileobj efficiently copies file streams to avoid loading large files into memory.
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file.filename)

    # 3. [Response] Return list of saved files
    return {"status": "uploaded", "files": saved_files}

@app.get("/api/download")
async def download_file(path: str):
    """
    File Download Interface.

    Goals:
    1. Download files based on their absolute path.
    2. Enforce strict security checks to prevent unauthorized access.
    """
    # 1. [Security Check] Path resolution and access control
    try:
        abs_path = Path(path).resolve()
        output_abs = output_dir.resolve()

        # Ensure the requested file is within the output directory
        if not abs_path.is_relative_to(output_abs):
            return {"error": "Access denied: Can only download files from the output directory"}
    except Exception:
        return {"error": "Invalid path parameter"}
    
    # 2. [Existence Check]
    if not abs_path.exists():
        return {"error": "File not found"}

    # 3. [Response] Return file stream
    return FileResponse(abs_path, filename=abs_path.name)

@app.get("/api/files")
async def list_files(path: str):
    """
    File Explorer Interface.

    Goals:
    1. List all generated files in the specified directory.
    2. Provide file metadata (size, time).
    3. Strict security check to prevent path traversal attacks.
    """
    print(f"[DEBUG] Requested file list: {path}")

    try:
        # 1. [Parse] Get absolute path
        abs_path = Path(path).resolve()
        output_abs = output_dir.resolve()

        # 2. [Security] Check for path traversal
        if not abs_path.is_relative_to(output_abs):
            print(f"[ERROR] Access denied: {abs_path} is not in {output_abs}")
            return {"error": "Access denied: Can only access files within the output directory"}

    except Exception as e:
        print(f"[ERROR] Path parsing failed: {e}")
        return {"error": f"Invalid path: {e}"}

    # 3. [Check] Does directory exist?
    if not abs_path.exists():
        return {"error": "Directory does not exist"}

    files = []
    try:
        # 4. [Traverse] Find all files recursively
        for file_path in abs_path.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "type": "file",
                    "path": str(file_path),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime
                })

    except Exception as e:
        print(f"[ERROR] File traversal failed: {e}")
        return {"error": str(e)}

    # 5. [Sort] Sort by modification time descending (latest first)
    files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    print(f"[DEBUG] Found {len(files)} files")
    return {"files": files}

@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """
    WebSocket Real-time Communication Core.

    Goals:
    1. Establish a long-lived connection for bidirectional communication.
    2. Bind to 'thread_id' to implement session-level isolation.
    """
    # 1. [Register] Establish connection and bind to manager
    await manager.connect(websocket, thread_id)

    try:
        # 2. [Loop] Maintain connection
        while True:
            # 3. [Listen] Receive messages (usually heartbeat pings)
            data = await websocket.receive_text()

            # 4. [Respond] Send pong
            await websocket.send_json({
                "type": "pong",
                "message": f"Server received: {data}"
            })

    except WebSocketDisconnect:
        # 5. [Cleanup] Client disconnected
        manager.disconnect(websocket, thread_id)
        print(f"[WebSocket] Client disconnected: {thread_id}")

    except Exception as e:
        # 6. [Error] Connection exception
        print(f"[WebSocket] Connection exception: {e}")
        manager.disconnect(websocket, thread_id)

if __name__ == "__main__":
    uvicorn.run("api.server:app", host="0.0.0.0", port=8001, reload=True)