# SunBun Solar Assistant Backend

This repository contains the backend and frontend systems for the SunBun Solar AI Assistant, built using LangGraph, FastAPI, and Next.js. The assistant acts as a deterministic state machine, flawlessly routing inquiries for both **Sales Support** and **Service Support**, handling dynamic user interactions, authentication, missing record pathways, and progressive data collection.

## Application Architecture

- **LangGraph Routing Engine (`src/graph.py`):** Acts as the central state machine graph, intelligently routing conversations and managing conversation state progression.
- **Support Workflows (`src/nodes/`):** Dedicated Python modules containing isolated flow logic for authentication (`auth.py`), CRM lookup (`lookup.py`), Service routing (`service.py`), unregistered fallback (`unregistered.py`), and Sales routing (`sales.py`).
- **FastAPI Server (`app.py`):** Wraps the graph definition into a local streaming Web Server complying with the unified Agent Protocol.
- **Next.js Frontend (`apps/web`):** The React-based conversation UI displaying dynamic support choices and proposals.

## 📸 Screenshots
### Service Support
<img width="632" height="906" alt="image" src="https://github.com/user-attachments/assets/58b6c3d3-3988-4435-937c-1de42de1276c" />

<img width="587" height="903" alt="image" src="https://github.com/user-attachments/assets/a2b5104d-fd9a-4b88-b934-604a06cc1ab7" />

<img width="550" height="380" alt="image" src="https://github.com/user-attachments/assets/db80788c-609e-4a98-8aa0-c2c11c2f1899" />

<img width="654" height="880" alt="image" src="https://github.com/user-attachments/assets/957806e2-5893-45ba-b17d-2b822e946a95" />

<img width="597" height="880" alt="image" src="https://github.com/user-attachments/assets/00a0541e-3a7c-4330-bd3d-50455a63fa1c" />

<img width="578" height="868" alt="image" src="https://github.com/user-attachments/assets/f389d930-ebd6-4ca6-aca0-1947e481d117" />


### Sales Support
<img width="592" height="906" alt="image" src="https://github.com/user-attachments/assets/daabb249-2245-4ad6-8b03-4053beefb183" />

<img width="641" height="902" alt="image" src="https://github.com/user-attachments/assets/b48474d8-2afb-4506-b9ca-39623af90cd9" />

<img width="621" height="908" alt="image" src="https://github.com/user-attachments/assets/b510ba46-df4b-4ef6-8288-c6a587dc32a5" />

<img width="578" height="908" alt="image" src="https://github.com/user-attachments/assets/9538b3f8-e925-4978-be04-5c71ca9b3881" />

<img width="558" height="891" alt="image" src="https://github.com/user-attachments/assets/9c9e6374-da2b-4d72-a56e-a46a317d403f" />

<img width="587" height="679" alt="image" src="https://github.com/user-attachments/assets/c77af6eb-5a3c-4308-80e3-43b581a00c51" />



## Running the Application Locally

The project consists of two separate components that must both be running simultaneously: 

### 1. Start the Python Backend
The backend utilizes Python and FastAPI to manage the core logic. 

```bash
# From the root directory:
python app.py
```
*The backend server will successfully boot up on `http://localhost:2024`.*

### 2. Start the Next.js Frontend UI
The UI manages user interface components like checkboxes and buttons via React.

```bash
# In a new, separate terminal tab, deploy the web server:
cd apps/web
pnpm run dev
```
*The React UI will launch and become accessible within your web browser on `http://localhost:3000`.*

## System Capabilities

### 1. Robust Service Workflows
- Full-fledged Authentication with OTP validation.
- Live database queries parsing user accounts. 
- Auto-routing for identified technical issues based on specific hardware queries.
- Smooth transition sequences into "Unregistered" logic tunnels. 
- Progressive multi-turn dialogs pausing on specific graph nodes for data collection.

### 2. Proposal Generation & CRM Logic
- Extracts user data to match and list existing proposals cleanly.
- Capable of generating brand-new proposal cards dynamically.
- Automatically handles CRM ticket creation (via fake system ID tracking).
- Live-Agent Support handover simulation (with simulated availability checking).
- Ambiguous prompt matching ("Sales" or "Service" directly typed into chat vs strict button-click dependencies).
