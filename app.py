import os
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from hindsight_client import Hindsight

load_dotenv()

st.set_page_config(
    page_title="MemorySupport AI",
    page_icon="🧠",
    layout="wide",
)

BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "memorysupport-demo")
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = """
You are MemorySupport AI, a professional customer support agent.

You have access to long-term customer memory supplied below.

Use remembered facts when they are relevant to the customer's current request.
Never invent customer history.
If memories conflict, do not guess which one is correct.

When relevant, explicitly acknowledge important remembered details naturally.
For example:
"Welcome back, Ananya. I remember your previous PDF upload issue."
"I remember that clearing the cache did not resolve the problem, so let's not repeat that step."

Do not ask the customer to repeat information that is already available in memory.
Avoid repeating troubleshooting steps that memory shows have already failed.

Use the customer's remembered name when it is reliable and relevant.
If the customer's name is conflicting or unclear, do not use a name.

Be concise, empathetic, and practical.
Give numbered steps when troubleshooting.

At the end, state whether the issue appears resolved, still open, or needs escalation.
"""


def get_clients():
    hindsight_key = os.getenv("HINDSIGHT_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    if not hindsight_key or not groq_key:
        return None, None, "Missing HINDSIGHT_API_KEY or GROQ_API_KEY in .env"

    @st.cache_resource(show_spinner=False)
    def _make_clients(hs_key: str, g_key: str, base_url: str):
        hs = Hindsight(base_url=base_url, api_key=hs_key, timeout=60.0)
        gr = Groq(api_key=g_key)
        return hs, gr

    return (*_make_clients(hindsight_key, groq_key, HINDSIGHT_BASE_URL), None)


hindsight, groq, setup_error = get_clients()

st.title("🧠 MemorySupport AI")
st.caption("A customer-support agent that remembers what happened before.")

with st.sidebar:
    st.header("Demo Controls")
    customer_id = st.text_input("Customer ID", value="CUST-1001")
    customer_name = st.text_input("Customer Name", value="Ananya")
    st.divider()

    if setup_error:
        st.error(setup_error)
        st.info("Create .env from .env.example, add your two API keys, then restart Streamlit.")
    else:
        st.success("Hindsight + Groq connected")

    if st.button("🌱 Seed Demo Customer", use_container_width=True, disabled=setup_error is not None):
        demo_memories = [
            f"Customer {customer_id} is named {customer_name}.",
            f"Customer {customer_id} uses Windows 11 and Chrome for work.",
            f"Customer {customer_id} previously reported that PDF uploads caused the application to crash.",
            f"For customer {customer_id}, clearing the application cache was tried previously and did not permanently solve the PDF upload crash.",
            f"Customer {customer_id} prefers step-by-step troubleshooting instructions.",
            f"Customer {customer_id} had a previous high-priority support ticket TKT-1042 about PDF upload crashes; the issue remained unresolved after cache clearing.",
        ]
        try:
            with st.spinner("Writing customer history to Hindsight..."):
                for memory in demo_memories:
                    hindsight.retain(
                        bank_id=BANK_ID,
                        content=memory,
                        context="Customer support history",
                        metadata={"customer_id": customer_id, "source": "demo_seed"},
                    )
            st.success("Demo customer memory seeded.")
        except Exception as exc:
            st.error(f"Could not seed memory: {exc}")

    if st.button("🧠 Generate Memory Summary", use_container_width=True, disabled=setup_error is not None):
        try:
            with st.spinner("Hindsight is synthesizing customer history..."):
                summary = hindsight.reflect(
                    bank_id=BANK_ID,
                    query=f"Summarize the most important support history, environment, preferences, failed troubleshooting steps, and unresolved issues for customer {customer_id}.",
                    context="Prepare a concise support-agent briefing.",
                    budget="mid",
                )
            st.session_state["memory_summary"] = summary.text
        except Exception as exc:
            st.error(f"Could not generate summary: {exc}")

    if "memory_summary" in st.session_state:
        st.divider()
        st.subheader("Hindsight Summary")
        st.write(st.session_state["memory_summary"])

st.subheader("Support Conversation")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Describe the customer's issue..."):
    if setup_error:
        st.error("Add your API keys to .env first.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    recall_text = "No relevant long-term memory was found."
    try:
        with st.spinner("Recalling relevant customer history from Hindsight..."):
            recall_result = hindsight.recall(
                bank_id=BANK_ID,
                query=f"Customer {customer_id}: {prompt}",
                max_tokens=3500,
                budget="mid",
            )
        if recall_result.results:
            recall_lines = []
            for memory in recall_result.results[:8]:
                text = getattr(memory, "text", str(memory))
                recall_lines.append(f"- {text}")
            recall_text = "\n".join(recall_lines)
    except Exception as exc:
        st.warning(f"Memory recall failed; continuing without long-term context: {exc}")

    recent_history = st.session_state.messages[-8:]
    response_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "RELEVANT LONG-TERM MEMORY FROM HINDSIGHT:\n"
                + recall_text
                + "\n\nCURRENT CUSTOMER ID: "
                + customer_id
            ),
        },
    ] + recent_history

    try:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                completion = groq.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=response_messages,
                    temperature=0.2,
                    max_tokens=700,
                )
                answer = completion.choices[0].message.content
            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})

        # Retain the useful interaction so later turns can benefit from it.
        interaction = (
            f"Customer {customer_id} support interaction at "
            f"{datetime.now(timezone.utc).isoformat()}.\n"
            f"Customer message: {prompt}\n"
            f"Assistant response: {answer}"
        )
        try:
            hindsight.retain(
                bank_id=BANK_ID,
                content=interaction,
                context="Customer support conversation",
                metadata={"customer_id": customer_id, "source": "live_chat"},
            )
        except Exception as exc:
            st.warning(f"Response was generated, but the interaction could not be stored in Hindsight: {exc}")

    except Exception as exc:
        st.error(f"Could not generate the support response: {exc}")

st.divider()
st.subheader("🔎 What Hindsight Recalled")

if setup_error:
    st.info("Connect Hindsight to see recalled memories here.")
else:
    if st.button("Refresh Recalled Memories", use_container_width=False):
        st.session_state["refresh_memory"] = True

    try:
        query = f"Customer {customer_id} support history and previous troubleshooting for the current issue"

        memories = hindsight.recall(
            bank_id=BANK_ID,
            query=query,
            max_tokens=3500,
            budget="mid"
        )

        if memories.results:
            unique_memories = []
            seen = set()

            for memory in memories.results:
                mem_text = getattr(memory, "text", str(memory))
                mem_type = getattr(memory, "type", "memory")

                key = (mem_type, mem_text.strip())

                if key not in seen:
                    seen.add(key)
                    unique_memories.append(
                        (mem_type, mem_text.strip())
                    )

            for index, (mem_type, mem_text) in enumerate(
                unique_memories[:8], start=1
            ):
                st.markdown(
                    f"**{index}. [{mem_type}]** {mem_text}"
                )

        else:
            st.info(
                "No memories found yet. "
                "Click 'Seed Demo Customer' or start a conversation."
            )

    except Exception as exc:
        st.info(f"Memory panel unavailable: {exc}")