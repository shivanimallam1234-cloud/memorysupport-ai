# MemorySupport AI

A customer-support AI agent that remembers customer history, environment, previous troubleshooting steps, preferences, and unresolved issues using Hindsight.

## Why this project

Traditional support bots often treat each conversation as a fresh interaction. MemorySupport AI uses Hindsight to retain useful information and recall relevant history before generating a response.

## Technology

- Python
- Streamlit
- Hindsight Cloud
- Groq (`openai/gpt-oss-120b`)

## Hindsight usage

The project demonstrates all three core memory operations:

1. **Retain** — saves customer history and useful support interactions.
2. **Recall** — retrieves relevant memories before answering.
3. **Reflect** — generates a support-agent briefing from accumulated memory.

## Run locally

1. Install Python 3.10+.
2. Create and activate a virtual environment.
3. Install packages:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and add:
   - `HINDSIGHT_API_KEY`
   - `GROQ_API_KEY`
5. Start the app:

```bash
streamlit run app.py
```

## Demo flow

1. Open the app.
2. Click **Seed Demo Customer**.
3. Ask: `My application is crashing again when I upload a PDF.`
4. Show that the agent remembers Windows 11, Chrome, the previous PDF-upload issue, the failed cache-clearing attempt, and the customer's preference for step-by-step instructions.
5. Click **Generate Memory Summary** to demonstrate Hindsight Reflect.
6. Open **What Hindsight Recalled** to make the memory layer visible to judges.

## Important

Never commit `.env` or API keys to GitHub.
