# from agent.subagents.knowledge_base_agent import knowledge_base_agent
from agent.subagents.database_query_agent import database_query_agent
from agent.subagents.network_search_agent import network_search_agent
from langgraph.checkpoint.memory import InMemorySaver
 
# Import main agent tools
from tools.markdown_tools import generate_markdown
from tools.pdf_tools import convert_md_to_pdf
from tools.upload_file_read_tool import read_file_content
 
from deepagents import create_deep_agent
 
from agent.llm import model
from agent.prompts import main_agent_content
 
from api.monitor import monitor
import asyncio
import uuid
import shutil
from pathlib import Path
 
from api.context import set_session_context, reset_session_context, set_thread_context
 
from langchain_core.messages import AIMessage
 
# Initialize the main agent
main_agent = create_deep_agent(
   model=model,
   system_prompt=main_agent_content['system_prompt'],
   tools=[generate_markdown, convert_md_to_pdf, read_file_content],
   checkpointer=InMemorySaver(),
   subagents=[
       database_query_agent,
       network_search_agent,
       # knowledge_base_agent
   ]
)
 
"""
  Execution Logic:
  1. Main agent execution must be asynchronous to support concurrent clients.
  2. The process is triggered by the FastAPI endpoint, initiating the main_agent's async execution.
  3. Main_agent utilizes stream-based processing to call tools and sub-agents.
  4. Monitoring hooks are implemented to:
     - Detect tool/sub-agent calls (name='task') and report via monitor to the frontend.
     - Push final results to the frontend.
     - Configure the session-specific output directory upon initialization.
"""
 
project_root_path = Path(__file__).parents[1].resolve()
 
async def run_deep_agent(task_query, session_id):
    """
    Defines the asynchronous, stream-based execution of the main agent.
    
    Args:
        task_query: The query from the frontend.
        session_id: Unique identifier for the user session.
    """
    print(f"Main agent execution started for session: {session_id}")
    
    # 1. Prepare Workspace: Create session-specific output directory
    session_dir = project_root_path / "output" / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir_str = str(session_dir).replace("\\", "/")
    
    # Get relative path for the LLM
    relative_session_dir_str = str(session_dir.relative_to(project_root_path)).replace("\\", "/")
 
    # 2. Handle uploaded files
    updated_dir_path = project_root_path / "updated" / f"session_{session_id}"
    updated_info_prompt = "" 
    
    if updated_dir_path.exists():
        files = [f.name for f in updated_dir_path.iterdir() if f.is_file()]
        if files:
            for filename in files:
                # Copy original file to output directory (retaining metadata)
                shutil.copy2(updated_dir_path / filename, session_dir / filename)
            
            # Construct instruction prompt for the model
            updated_info_prompt = (f"\n    [Uploaded Files] loaded into workspace:\n" +
                             "\n".join([f"    - {f}" for f in files]) +
                             "\n    Please prioritize using the 'read_file_content' tool to reference these files.")
 
    # 3. Context Management: Store session_id and directory in ContextVars
    session_dir_token = set_session_context(session_dir_str)
    session_id_token = set_thread_context(session_id)
 
    # Notify frontend of the session directory
    monitor.report_session_dir(session_dir_str)
 
    # 4. Prepare agent configuration
    config = {
        "configurable": {
            "thread_id": session_id
        }
    }
 
    # 5. Build Instruction Prompt
    path_instruction = f"""
    【Workspace Instructions】
    Working Directory: {relative_session_dir_str}
    {updated_info_prompt}
 
    Rules:
    1. Newly generated files must be saved to the working directory: '{relative_session_dir_str}/filename'
    2. When reading uploaded files, pass only the filename (e.g., 'intro.txt') to the 'read_file_content' tool. Do not include directory prefixes.
    3. Use relative paths only; absolute paths are prohibited.
    4. If uploaded files exist, analyze them first.
    """
 
    # 6. Execute Main Agent
    try:
        async for chunk in main_agent.astream({
            "messages": [
                {"role": "user", "content": task_query + path_instruction}
            ]
        }, config=config):
            
            for node_name, state in chunk.items():
                if not state or "messages" not in state: continue
                messages = state["messages"]
                
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if node_name == 'model':
                        if last_msg.tool_calls:
                            # Handle Tool/Sub-agent calls
                            for tool_call in last_msg.tool_calls:
                                if tool_call['name'] == 'task':
                                    monitor.report_assistant(
                                        tool_call['args']['subagent_type'],
                                        {'description': tool_call['args']['description']}
                                    )
                        elif last_msg.content:
                            # Report final results
                            print(f"Main agent result: {last_msg.content[:100]}...")
                            monitor.report_task_result(last_msg.content)
 
    except Exception as e:
        monitor._emit("error", f"Main agent execution failed: {str(e)}")
        
    finally:
        # Cleanup ContextVars
        reset_session_context(session_dir_token, session_id_token)