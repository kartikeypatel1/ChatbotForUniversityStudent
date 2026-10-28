"""Streamlit UI.  Run with:  streamlit run src/app.py"""
import sys
import uuid
from pathlib import Path
import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
import db  # noqa: E402
from nlp import HELPDESK_CONTACT, REASON_TEXT, Bot  # noqa: E402

st.set_page_config(page_title="Student Support Assistant", page_icon="🎓")
# Custom CSS for modern, premium UI
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #1e1e2f, #29293d);
        color: #e0e0e0;
    }
    .sidebar .sidebar-content {
        background: rgba(30,30,45,0.85);
        padding: 1rem;
        border-radius: 12px;
    }
    .stButton>button {
        background-color: #4e9af1;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #3578c5;
    }
    .chat-bubble {
        padding: 0.75rem 1rem;
        border-radius: 12px;
        margin: 0.5rem 0;
    }
    .assistant { background: #2b2b3a; }
    .user { background: #0f4c81; color: #fff; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_bot():
    return Bot()


@st.cache_resource
def get_conn():
    return db.connect()

# Helper to render chat messages with styled bubbles, timestamps, and escalation warnings
def render_message(msg):
    """Render a single chat message with proper styling.
    msg: dict with keys 'role', 'content', optional 'timestamp' (datetime), optional 'escalated' (bool) and 'reason_text' (str).
    """
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    ts = msg.get("timestamp")
    ts_str = f"<span style='font-size:0.8em;color:#888;'>{ts.strftime('%H:%M')}</span>" if isinstance(ts, datetime.datetime) else ""
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
    st.session_state.session_id = uuid.uuid4().hex[:12]   # random, not linked to the student
    st.session_state.messages = []

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("🎓 Student Support")
    page = st.radio("View", ["Chat", "Agent view (escalations)"])
    st.subheader("Privacy")
    opted_out = st.checkbox("Don't save my chat (opt out)", help="Nothing from this chat is written to the database.")
    st.caption("Chats are stored only as scrubbed text under a random session ID. "
               "Emails, phone numbers and ID numbers are masked before saving.")
    if st.button("🗑️ Delete my session data"):
        db.delete_session(conn, st.session_state.session_id)
        st.session_state.messages = []
        st.success("Your saved chat data for this session was deleted.")
        if st.button("🧹 Clear chat history"):
            st.session_state.messages = []
            st.success("Chat history cleared.")

# --------------------------------------------------------------------- chat
if page == "Chat":
    st.title("Student Support Assistant")
    st.info("I'm an automated assistant, not a person. Please don't share personal details such as "
            "your name, ID number or phone number. Ask me to talk to a human at any time.")

    for m in st.session_state.messages:
        # Render each message with custom bubbles and timestamps
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

    if prompt := st.chat_input("Ask about admissions, fees, housing, courses, IT, wellbeing..."):
        res = bot.respond(prompt)
        log_id = None if opted_out else db.log_turn(conn, st.session_state.session_id, res)
        reply = res["reply"]
        if res["escalated"] and opted_out:
            reply += (f" Because you opted out, nothing is saved, so no one will see this chat. "
                      f"Please contact the helpdesk directly: {HELPDESK_CONTACT}.")
        st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": datetime.datetime.now()})
        st.session_state.messages.append({
            "role": "assistant",
            "content": reply,
            "log_id": log_id,
            "escalated": res["escalated"],
            "reason_text": REASON_TEXT.get(res["reason"], ""),
            "timestamp": datetime.datetime.now(),
        })
        st.rerun()

# -------------------------------------------------------------- agent view
else:
    st.title("Agent view - escalated chats")
    st.caption("Demo of the human-agent side. Shows only scrubbed text from users who did not opt out.")
    df = db.escalations_df(conn)
    st.dataframe(df, use_container_width=True) if len(df) else st.write("No escalations yet.")
