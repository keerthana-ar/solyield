# SunBun Solar Assistant - LEVEL 2 (Aegra Ready)

This repository contains the advanced Level 2 implementation of the SunBun Solar AI Assistant. It is built using **LangGraph**, **FastAPI**, and **Next.js**, featuring a proactive high-order agent architecture and official **Agent Protocol** alignment.

The assistant acts as a sophisticated state machine, intelligently managing:
- **Sales Support**: Proactive AI assistant with design recommendations and agent feedback loops.
- **Service Support**: Multi-turn resolution with satisfaction tracking (NPS) and ticket generation.
- **Authentication**: Seamless OTP-based identification with CRM lookup bypass.

## 🚀 Level 2 & Week 2 Bonus Features

### 1. Proactive AI Sales Assistant (Bonus)
The AI doesn't just list options; it acts as a **Sales Assistant to YOU**. Once proposals are generated, the AI proactively recommends the top design, offers to list more details, and waits for your (the sales agent's) feedback before sharing with the customer.

### 2. Zero-Metadata SSE Streaming
A custom, lightning-fast **Server-Sent Events (SSE)** protocol. By stripping metadata overhead and strictly adhering to the `values` event schema, the backend provides 100% compatibility with the LangGraph React SDK, eliminating `StreamError` crashes.

### 3. Agent Protocol (ap/v1) Readiness
The FastAPI layer is architected to support standard Agent Protocol endpoints, ensuring that conversation persistence and task tracking are ready for production deployment on platforms like LangGraph Aegra.

### 4. Optimized In-Memory Persistence
Using `MemorySaver`, the assistant handles multi-turn state transitions with ultra-low latency, making it perfect for high-speed hackathon demonstrations.

## 📸 Screenshots
### Service & Sales Flows
*(See image links below for high-order routing and design options)*

<img width="632" height="906" alt="image" src="https://github.com/user-attachments/assets/58b6c3d3-3988-4435-937c-1de42de1276c" />
<img width="592" height="906" alt="image" src="https://github.com/user-attachments/assets/daabb249-2245-4ad6-8b03-4053beefb183" />

## 🛠️ Running the Application Locally

### 1. Start the Python Backend
The backend runs on FastAPI and exposes the graph via a streaming endpoint.

```powershell
# From the root directory:
$env:PYTHONPATH="."
python src/server.py
```
*Backend runs on `http://localhost:8000`.*

### 2. Start the React UI
The frontend uses the `@langchain/langgraph-sdk` to communicate with the backend.

```bash
# In a new terminal tab:
cd my-agent-ui
npm run dev
```
*Frontend runs on `http://localhost:3000`.*

## 🏗️ Application Architecture

- **LangGraph Core (`src/graph.py`):** Central state machine with conditional routing and sub-graph logic.
- **Support Workflows (`src/nodes/`):** Isolated modules for Sales, Service, Entry, and Authentication.
- **Clean Persistence:** All conversation data is handled in-memory for the demo, anchored by `thread_id`.
- **Protocol-Aligned SSE**: Reliable real-time updates for complex multi-node transitions.
