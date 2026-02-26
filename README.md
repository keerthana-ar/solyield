# SunBun Solar Assistant (Week 1)

A deterministic state-graph backend for a solar sales and service assistant, built with **LangGraph** and integrated with actual customer/site data.

## 🚀 Project Overview
SunBun is an intelligent Solar Sales & Service Assistant designed to provide seamless support for both existing customers and new prospects. By utilizing a deterministic state-graph architecture, the assistant ensures reliable, turn-based interactions compliant with the SunBun brand guidelines.

### Architecture & Approach
We utilized **LangGraph** to build a robust, circular, and modular state machine. Unlike standard LLM chatbots, our approach is **governed by deterministic nodes**, ensuring:
1. **Consistency**: Every user follows the same verified logic paths (Step 1-8).
2. **Reliability**: No LLM hallucinations in pricing, sizing, or technical diagnosis during Week 1.
3. **Traceability**: Every state transition is tracked via a typed `State` object.

```mermaid
graph TD
    Entry[Entry Node] --> Router{Support Router}
    Router -- Service --> Auth[Auth Flow]
    Router -- Sales --> Auth
    Auth --> Lookup[Customer Lookup]
    Lookup -- Found --> ServiceCheck[Service Status / Case B]
    Lookup -- Not Found --> Unreg[Unregistered Flow / Prospect Sales]
    ServiceCheck --> Resolution{Resolution?}
    Resolution -- Unhappy --> Capture[Issue Capture]
    Resolution -- Happy --> NPS[NPS & Close]
    Capture --> Ticket[Ticket Create]
    Unreg --> Ticket
    Lookup -- Found (Sales) --> SalesGreet[Proposal Review]
    SalesGreet --> SalesCapture[New Proposal Data]
    SalesCapture --> Generate[Proposal Generation]
    Generate --> Confirm[Sales Handoff/Confirm]
```

## 📸 Screenshots
<img width="592" height="906" alt="image" src="https://github.com/user-attachments/assets/daabb249-2245-4ad6-8b03-4053beefb183" />

<img width="641" height="902" alt="image" src="https://github.com/user-attachments/assets/b48474d8-2afb-4506-b9ca-39623af90cd9" />

<img width="621" height="908" alt="image" src="https://github.com/user-attachments/assets/b510ba46-df4b-4ef6-8288-c6a587dc32a5" />

<img width="578" height="908" alt="image" src="https://github.com/user-attachments/assets/9538b3f8-e925-4978-be04-5c71ca9b3881" />

<img width="558" height="891" alt="image" src="https://github.com/user-attachments/assets/9c9e6374-da2b-4d72-a56e-a46a317d403f" />

<img width="587" height="679" alt="image" src="https://github.com/user-attachments/assets/c77af6eb-5a3c-4308-80e3-43b581a00c51" />



## 🎥 Video Walkthrough
[![SunBun Solar Assistant Walkthrough](https://img.shields.io/badge/Video-Watch%20Walkthrough-red?style=for-the-badge&logo=youtube)](https://example.com/sunbun-video)
*(Placeholder link: Replace with actual video demonstration URL)*

## 🛠 Features
- **Deterministic Routing**: Automated branching for Sales vs. Service support.
- **OTP Authentication**: Robust 3-turn loop with failover paths.
- **Service Case B Analysis**: Automated computation of cloudiness and production averages.
- **Sales Proposal Engine**: Deterministic sizing logic based on electricity bill and tier preferences.
- **Agent Protocol Compatibility**: Ready for integration with standards-based frontends.

## ⚙️ Setup & Execution
1. **Install Requirements**:
   ```bash
   pip install langgraph-cli pandas fastapi uvicorn
   ```
2. **Launch LangGraph API Server (for Agent Chat)**:
   ```bash
   python -m langgraph_cli dev
   ```
   *Note: This starts the server on `http://localhost:2024`.*

3. **Connect to Agent Chat UI**:
   - Open [agentchat.vercel.app](https://agentchat.vercel.app/) in your browser.
   - Enter `http://localhost:2024` as the **Deployment URL**.
   - Enter `agent` as the **Assistant / Graph ID**.
   - Click **Continue** to start interacting with SunBun!

4. **Run All Verifications (Internal)**:
   ```bash
   python run_all_tests.py
   ```

---
**SunBun Solar Assistant** - *Empowering sustainable energy through intelligent assistance.*
=======
