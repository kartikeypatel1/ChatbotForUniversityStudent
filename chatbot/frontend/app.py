# Streamlit Front‑End for the AI‑Powered Chatbot
# This file replicates the original UI (src/app.py) but lives in a dedicated
# `frontend` directory. It keeps the same premium styling and functionality
# while adjusting the Python import path so that the backend modules in
# `src/` (db, nlp, etc.) can be imported.

"""Streamlit UI.  Run with:  streamlit run frontend/app.py"""
import sys
import uuid
from pathlib import Path
import datetime

import streamlit as st

# Add the `src` directory to the Python path so that we can import the
# backend modules (`db`, `nlp`, etc.) which remain unchanged.
# `frontend/app.py` is one level deeper than the project root, so we go up
# one directory and then into `src`.
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

# Now imports work as they did in the original app.
import db  # noqa: E402
from nlp import HELPDESK_CONTACT, REASON_TEXT, Bot  # noqa: E402
# FLAN‑T5 helper
from model import get_answer  # noqa: E402

st.set_page_config(page_title="Student Support Assistant", page_icon="🎓")

@st.cache_resource
def get_bot():
    return Bot()

@st.cache_resource
def get_conn():
    return db.connect()

# Helper to render chat messages with styled bubbles, timestamps, and
# escalation warnings

def render_message(msg):
    """Render a single chat message with proper styling.
    msg: dict with keys 'role', 'content', optional 'timestamp' (datetime),
    optional 'escalated' (bool) and 'reason_text' (str).
    """
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    ts = msg.get("timestamp")
    ts_str = (
        f"<span style='font-size:0.8em;color:#888;'>{ts.strftime('%H:%M')}</span>"
        if isinstance(ts, datetime.datetime)
        else ""
    )
    escalation_html = ""
    if msg.get("escalated"):
        reason = msg.get("reason_text", "")
        escalation_html = f"<div style='color:#ff6;font-weight:bold;'>⚠️ Escalated: {reason}</div>"
    html = f"""
    <div class='chat-bubble {role}'>
        {ts_str}<br>{escalation_html}{content}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

bot, conn = get_bot(), get_conn()

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:12]  # random, not linked to the student
    st.session_state.messages = []

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("🎓 Student Support")
    page = st.radio("View", ["Chat", "Agent view (escalations)"], key="view_selector")
    st.subheader("Privacy")
    opted_out = st.checkbox(
        "Don't save my chat (opt out)",
        help="Nothing from this chat is written to the database.",
        key="chat_opt_out_checkbox",
    )
    st.caption(
        "Chats are stored only as scrubbed text under a random session ID. "
        "Emails, phone numbers and ID numbers are masked before saving."
    )
    if st.button("🗑️ Delete my session data"):
        db.delete_session(conn, st.session_state.session_id)
        st.session_state.messages = []
        st.success("Your saved chat data for this session was deleted.")
    if st.button("🧹 Clear chat history", key="clear_chat_history_button"):
        st.session_state.messages = []
        st.success("Chat history cleared.")
    # Experimental FLAN toggle
    use_flan = st.checkbox("Use FLAN‑T5 (experimental)", value=False, key="use_flan_checkbox")

# --------------------------------------------------------------------- chat
if page == "Chat":
    st.title("Student Support Assistant")
    st.info(
        "I'm an automated assistant, not a person. Please don't share personal "
        "details such as your name, ID number or phone number. Ask me to talk "
        "to a human at any time."
    )

    for m in st.session_state.messages:
        render_message(m)
        # Show rating buttons for assistant messages
        if m["role"] == "assistant" and m.get("log_id") and not m.get("rated"):
            c1, c2, _ = st.columns([1, 1, 6])
            if c1.button("👍", key=f"up{m['log_id']}"):
                db.rate(conn, m["log_id"], 5)
                m["rated"] = True
                st.rerun()
            if c2.button("👎", key=f"down{m['log_id']}"):
                db.rate(conn, m["log_id"], 1)
                m["rated"] = True
                st.rerun()

    if prompt := st.chat_input(
        "Ask about admissions, fees, housing, courses, IT, wellbeing..."
    ):
        # Store user message
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "timestamp": datetime.datetime.now()}
        )
        render_message({"role": "user", "content": prompt})

        # Generate answer
        with st.chat_message("assistant"):
            with st.spinner("Finding an answer..."):
                if use_flan:
                    answer = get_answer(prompt)
                    res = None  # FLAN path has no compatible response dict
                else:
                    res = bot.respond(prompt)
                    answer = res["reply"]
                    # Preserve escalation info on the user message for display
                    st.session_state.messages[-1]["escalated"] = res.get("escalated", False)
                    st.session_state.messages[-1]["reason_text"] = REASON_TEXT.get(res.get("reason"), "")
                st.write(answer)

        # Log turn to DB using the *complete* res dict (required by db.log_turn)
        log_id = None
        if not opted_out and res is not None:
            log_id = db.log_turn(conn, st.session_state.session_id, res)

        # Store assistant message
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "timestamp": datetime.datetime.now(),
                "log_id": log_id,
                "escalated": res.get("escalated", False) if res else False,
                "reason_text": REASON_TEXT.get(res.get("reason"), "") if res else "",
            }
        )
        st.rerun()

# -------------------------------------------------------------- agent view
else:
    st.title("Agent view - escalated chats")
    st.caption(
        "Demo of the human-agent side. Shows only scrubbed text from users who did not opt out."
    )
    df = db.escalations_df(conn)