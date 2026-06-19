import datetime
import asyncio
from typing import Any, Dict, Optional
from fastapi import WebSocket
from api.context import get_thread_context

# Attempt to import built-in runtime (for script-mode stream output)
try:
    import builtins
except ImportError:
    builtins = None


class ToolMonitor:
    """
    Tool monitoring class used to report progress and status during tool execution.
    Designed as a singleton to be imported and used directly within any tool.
    Compatible with both FastAPI WebSockets and script runtimes via stream_writer.

    Usage Example:
    from api.monitor import monitor

    def my_tool(arg1):
        monitor.report_start("my_tool", {"arg1": arg1})
        ...
        monitor.report_running("my_tool", "Processing data...", progress=0.5)
        ...
        monitor.report_end("my_tool", result)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolMonitor, cls).__new__(cls)
            cls._instance.websocket_manager = None  # Reserved for FastAPI WebSocketManager
        return cls._instance

    def set_websocket_manager(self, manager):
        """Set the FastAPI WebSocket manager."""
        self.websocket_manager = manager

    def _emit(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Internal emission method to dispatch events."""
        payload = {
            "type": "monitor_event",
            "event": event_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.datetime.now().isoformat()
        }

        # 1. Prioritize sending via FastAPI WebSocket (Targeted Push)
        if self.websocket_manager:
            try:
                thread_id = get_thread_context()
                manager_loop = self.websocket_manager.loop

                if manager_loop:
                    if thread_id:
                        try:
                            current_loop = asyncio.get_running_loop()
                        except RuntimeError:
                            current_loop = None

                        # If in the same event loop (e.g., running within create_task), 
                        # execute directly. Otherwise, use thread-safe scheduling.
                        if current_loop and current_loop == manager_loop:
                            current_loop.create_task(
                                self.websocket_manager.send_to_thread(payload, thread_id)
                            )
                        else:
                            # Use run_coroutine_threadsafe for cross-thread execution 
                            # to avoid "loop mismatch" errors.
                            asyncio.run_coroutine_threadsafe(
                                self.websocket_manager.send_to_thread(payload, thread_id),
                                manager_loop
                            )
            except Exception as e:
                print(f"[Monitor] WebSocket send failed: {e}")

        # 2. Try outputting via global runtime (DeepAgents script mode)
        # Enables MockRuntime in simple_agents.py to receive data
        if builtins and hasattr(builtins, 'runtime') and hasattr(builtins.runtime, 'stream_writer'):
            try:
                builtins.runtime.stream_writer(payload)
            except Exception:
                pass

        # 3. Console fallback output (for debugging)
        print(f"\n[Monitor:{event_type}] {message}")

    def report_tool(self, tool_name: str, args: Dict[str, Any] = None):
        """Report that a tool has started execution."""
        self._emit("tool_start", f"Tool started: {tool_name}", {"tool_name": tool_name, "args": args})

    def report_assistant(self, assistant_name: str, args: Dict[str, Any] = None):
        """Report progress of a sub-agent being called."""
        self._emit("assistant_call", f"Calling assistant: {assistant_name}",
                   {"assistant_name": assistant_name, "args": args})

    def report_task_result(self, result: str):
        """Report the final result of a task."""
        self._emit("task_result", "Task completed", {"result": result})

    def report_session_dir(self, path: str):
        """Report the task workspace directory."""
        self._emit("session_created", f"Workspace created: {path}", {"path": path})


# Global singleton instance
monitor = ToolMonitor()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.loop = None

    def set_loop(self, loop):
        """Explicitly set the event loop."""
        self.loop = loop
        monitor.set_websocket_manager(self)
        print(f"[Monitor] ConnectionManager manually bound to loop: {id(self.loop)}")

    async def connect(self, websocket: WebSocket, thread_id: str):
        await websocket.accept()
        print(f"Storing session ID {thread_id} for: {websocket}")
        self.active_connections[thread_id] = websocket
        print(f"Client connected: {thread_id}")

    def disconnect(self, websocket: WebSocket, thread_id: str):
        if thread_id in self.active_connections:
            del self.active_connections[thread_id]
        print(f"Client disconnected: {thread_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_to_thread(self, message: dict, thread_id: str):
        if thread_id in self.active_connections:
            websocket = self.active_connections[thread_id]
            await websocket.send_json(message)


manager = ConnectionManager()