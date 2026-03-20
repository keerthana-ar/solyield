# SunBun Solar Assistant - Final Demonstration Script 🏆☀️

Follow these 3 specific demos to showcase 100% compliance + all the bonus features.

## Demo 1: The "Crash Test" (States & Protocol Bonus)
*Proves the Agent Protocol compliance and that memory survives server restarts.*

1.  **Open Powershell** in the root folder.
2.  **Start Task**:
    ```powershell
    Invoke-RestMethod -Uri "http://localhost:8000/ap/v1/agent/tasks" `
      -Method Post `
      -Headers @{"Content-Type"="application/json"} `
      -Body '{"input": "Hi", "customer_id": "HACK_DEMO_01"}'
    ```
3.  **Command - Choose Sales**:
    ```powershell
    Invoke-RestMethod -Uri "http://localhost:8000/ap/v1/agent/tasks/HACK_DEMO_01/steps" `
      -Method Post `
      -Headers @{"Content-Type"="application/json"} `
      -Body '{"input": "sales"}'
    ```
4.  **THE CRASH**: Go to your Python backend terminal and press **`Ctrl + C`**. 
5.  **THE RESTORE**: Restart it with `python src/server.py`.
6.  **Proof of Persistence**: Send the next command (asking for email):
    ```powershell
    Invoke-RestMethod -Uri "http://localhost:8000/ap/v1/agent/tasks/HACK_DEMO_01/steps" `
      -Method Post `
      -Headers @{"Content-Type"="application/json"} `
      -Body '{"input": "email"}'
    ```
    *Result: The agent remembers you chose "Sales" and asks for your email address immediately!*

---

## Demo 2: The "Full Story" Show (Service) 🛠️
*Shows verbatim compliance and the interactive NPS loop.*

1.  Open the UI: `http://localhost:3000`.
2.  **Trigger**: Type "Service Support".
3.  **Identifier**: Enter **`jane.smith@example.com`** (Customer #2).
4.  **OTP**: `123456`.
5.  **The Narrative**: The agent will greet Jane and report an **"Inverter communication issue"** (matching `sites.csv` exactly).
6.  **The Choice**: Click **"I’m happy with this explanation"**.
7.  **Interactive NPS**:
    *   AI asks for a score (1-10). Type **`10`**.
    *   AI asks for feedback. Type **"Excellent solar monitoring!"**.
    *   AI confirms and closes.

---

## Demo 3: The "Sales Assistant" Show (Bonus) 🤝
*Shows the "Human-in-the-Loop" bonus where AI acts as your assistant.*

1.  In the UI, start a **Sales Support** flow.
2.  **Identifier**: **`john.doe@example.com`** (Customer #1).
3.  **OTP**: `123456`.
4.  Choose **"Create new proposals"**.
5.  Follow the prompts for design count (e.g., 3).
6.  **The "Assistant" Moment**: Once proposals are ready, the AI will address **YOU** (the sales agent):
    > *"Proposals generated. As a Sales Assistant, I recommend the [X]. I can also list the top 5 options from our design system. Do you have any feedback?"*
7.  Click **"Looks Good"**, then click **"Share with Customer"**.
8.  **The Final Step**: The AI asks: *"Would you like to initiate a live call or chat with the customer now?"*.

---
