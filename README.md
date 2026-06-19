# DeepAgents Multi-Source Research System

An autonomous multi-agent deep research system built on the **DeepAgents** framework, capable of self-planning, task decomposition, multi-source retrieval, and generating structured output reports.

## 📸 Demo

> User submits a research query → Main Agent plans and dispatches sub-agents → Web search + Database query run in parallel → Results aggregated → Markdown/PDF report generated

## 🏗️ Architecture

```
User Query
    │
    ▼
Main Agent (DeepAgents + LangGraph)
├── Planning: task decomposition via write_todos
├── Context Management: file system to prevent context overflow
├── Long-term Memory: cross-session memory via LangGraph Store
│
├── Sub-Agent 1: Network Search Agent
│   └── Tavily API → real-time web search
│
└── Sub-Agent 2: Database Query Agent
    └── MySQL → structured pharmaceutical data query
        └── Generates Markdown report
```

## ✨ Key Features

- **Autonomous Planning** — Main agent decomposes complex tasks into executable steps using `write_todos`, dynamically adjusting the plan during execution
- **Context Management** — Built-in file system tools (`read_file`, `write_file`, `ls`) prevent context window overflow for long-running tasks
- **Multi-Agent Coordination** — Sub-agents run with isolated context windows, preventing interference between parallel tasks
- **Long-term Memory** — Cross-session persistent memory via LangGraph Store; agent remembers previous interactions
- **Real-time Streaming** — WebSocket connection pushes live progress updates (tool calls, logs, results) to the frontend
- **Multi-source Retrieval** — Combines web search (Tavily) and structured database queries (MySQL) for comprehensive research

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | DeepAgents, LangChain, LangGraph |
| LLM | OpenAI GPT-4o-mini |
| Web Search | Tavily API |
| Database | MySQL |
| Backend API | FastAPI + WebSocket |
| Frontend | Vue.js + Vite |
| Context Management | File system (built-in DeepAgents) |
| Long-term Memory | LangGraph Store |
| Report Generation | Markdown → PDF (python-docx) |

## 📁 Project Structure

```
├── agent/
│   ├── subagents/
│   │   ├── database_query_agent.py   # MySQL sub-agent
│   │   └── network_search_agent.py   # Tavily web search sub-agent
│   ├── llm.py                        # LLM initialization
│   ├── main_agent.py                 # Main orchestrator agent
│   └── prompts.py                    # Prompt templates (loaded from YAML)
├── api/
│   ├── context.py                    # Shared session context
│   ├── monitor.py                    # WebSocket monitor for real-time updates
│   └── server.py                     # FastAPI server
├── tools/                            # Custom tool definitions
├── ui/                               # Vue.js frontend
│   ├── src/
│   ├── index.html
│   └── vite.config.js
├── utils/
│   ├── path_utils.py
│   └── word_converter.py             # Markdown to PDF converter
├── prompt/                           # YAML prompt files
├── output/                           # Generated reports (auto-created)
├── updated/                          # User uploaded files
├── sql/                              # Database schema and seed data
│   └── company_data.sql
├── .env                              # Environment variables (not committed)
└── requirements.txt
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- MySQL 8.0+
- Node.js 18+ (for frontend)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/DeepAgentsResearchSystem.git
cd DeepAgentsResearchSystem
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# Tavily Web Search
TAVILY_API_KEY=your_tavily_api_key

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=pharma_db
```

### 4. Set Up MySQL Database

```bash
mysql -u root -p < sql/company_data.sql
```

### 5. Start the Backend

```bash
python api/server.py
# Server runs at http://localhost:8000
```

### 6. Start the Frontend

```bash
cd ui
npm install
npm run dev
# Frontend runs at http://localhost:5173
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/task` | Submit a research task, returns `thread_id` |
| POST | `/api/upload` | Upload files for agent processing |
| GET | `/api/files` | List generated output files |
| GET | `/api/download` | Download a generated report |
| WS | `/ws/{thread_id}` | WebSocket for real-time progress updates |

## 💡 How It Works

1. **User submits a query** via the frontend chat interface
2. **Frontend establishes WebSocket** connection using `thread_id`
3. **FastAPI receives the request**, stores `thread_id` in shared context, triggers the main agent asynchronously
4. **Main Agent plans the task** — decomposes into sub-tasks using `write_todos`
5. **Sub-agents execute in parallel**:
   - Network Search Agent queries Tavily for real-time web results
   - Database Query Agent queries MySQL for structured data
6. **Monitor pushes real-time updates** (tool calls, logs, intermediate results) via WebSocket
7. **Main Agent aggregates results** and generates a Markdown report, optionally converting to PDF
8. **Frontend displays the final report** and allows file download

## 📊 Agent Coordination Pattern

```
Main Agent
├── [Planning]    write_todos → task list
├── [Dispatch]    task tool → spawn sub-agent
│   ├── Sub-Agent: network_search (isolated context)
│   └── Sub-Agent: database_query (isolated context)
├── [Aggregate]   collect sub-agent summaries
├── [Generate]    write final report to file system
└── [Notify]      monitor.send() → WebSocket → Frontend
```

## 🔑 Key Design Decisions

- **Sub-agents use isolated context windows** — prevents cross-contamination between retrieval sources
- **File system for context management** — avoids context overflow for long research tasks  
- **WebSocket over SSE** — enables bidirectional communication for future interactive features
- **Thread ID pattern** — allows multiple concurrent research sessions

## 📝 License

MIT
