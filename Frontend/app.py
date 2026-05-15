import streamlit as st
import requests
from datetime import datetime

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Interview Bot",
    page_icon="💬",
    layout="wide"
)

# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------
if "sessions" not in st.session_state:
    st.session_state.sessions = []

if "current_session" not in st.session_state:
    st.session_state.current_session = {
        "id": 0,
        "name": "New Chat",
        "messages": [],
        "created": datetime.now().strftime("%H:%M"),
    }

if "mode" not in st.session_state:
    st.session_state.mode = "interview"

if "interview_data" not in st.session_state:
    st.session_state.interview_data = {
        "questions": [],
        "answers": [],
        "current_q_index": 0,
        "waiting_for_answer": False,
        "interview_active": False,
        "user_name": "Candidate",
        "domain": "Healthcare Admin",
        "feedback_received": False,
        "feedbacks": []
    }

# -------------------------------------------------
# PREMIUM CSS (glassmorphism + glow input)
# -------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at 20% 30%, #0a0a0f 0%, #050510 100%);
        color: #E0E0E0;
    }
    header, #MainMenu, footer { visibility: hidden; }

    /* Sidebar glass */
    section[data-testid="stSidebar"] {
        background: rgba(15, 15, 25, 0.7);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    /* Chat bubbles */
    div[data-testid="stChatMessage"] {
        background: rgba(18, 18, 28, 0.8);
        backdrop-filter: blur(8px);
        border-radius: 24px;
        padding: 20px 26px;
        margin-bottom: 14px;
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: 0 8px 20px rgba(0,0,0,0.3);
        max-width: 85%;
        animation: fadeInUp 0.3s ease-out;
    }
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: linear-gradient(135deg, #1a2f4a, #0f1f2f);
        border: 1px solid rgba(100, 180, 255, 0.15);
        margin-left: auto;
        box-shadow: 0 8px 20px rgba(0,0,0,0.4);
    }
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background: linear-gradient(135deg, #141418, #1a1a22);
        border: 1px solid rgba(255,255,255,0.06);
    }

    /* Chat input - glass + glow focus */
    .stChatInput > div {
        background: rgba(18, 18, 28, 0.9);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        padding: 4px;
        transition: all 0.3s ease;
    }
    .stChatInput textarea {
        background: transparent !important;
        color: #EAEAEA !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 16px !important;
        padding: 14px 18px !important;
        border-radius: 18px !important;
        caret-color: #4ADE80;
    }
    .stChatInput > div:focus-within {
        border-color: #4ADE80 !important;
        box-shadow: 0 0 18px rgba(74, 222, 128, 0.15);
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #FFFFFF, #E0E0E0);
        color: #0A0A0A;
        border: none;
        border-radius: 14px;
        padding: 12px 24px;
        font-weight: 700;
        font-size: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #F0F0F0, #D0D0D0);
        box-shadow: 0 6px 18px rgba(0,0,0,0.4);
        transform: translateY(-1px);
    }
    .stDownloadButton > button {
        background: linear-gradient(135deg, #4ADE80, #22C55E);
        color: #0A0A0A;
        border: none;
        border-radius: 14px;
        padding: 10px 24px;
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(34,197,94,0.2);
    }
    .stDownloadButton > button:hover {
        box-shadow: 0 6px 16px rgba(34,197,94,0.3);
        transform: translateY(-1px);
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>

<script>
    const observer = new MutationObserver(() => {
        const inputs = window.parent.document.querySelectorAll('.stChatInput textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                const c = input.closest('.stChatInput > div');
                if (c) c.style.boxShadow = '0 0 22px rgba(74,222,128,0.2)';
            });
            input.addEventListener('blur', () => {
                const c = input.closest('.stChatInput > div');
                if (c) c.style.boxShadow = 'none';
            });
        });
    });
    observer.observe(window.parent.document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HELPER: Save session
# -------------------------------------------------
def save_current_session():
    sess = st.session_state.current_session
    if len(sess["messages"]) > 0:
        if not any(s["id"] == sess["id"] for s in st.session_state.sessions):
            st.session_state.sessions.append(sess.copy())
    new_id = max([s["id"] for s in st.session_state.sessions], default=0) + 1
    st.session_state.current_session = {
        "id": new_id,
        "name": "New Chat",
        "messages": [],
        "created": datetime.now().strftime("%H:%M"),
    }
    st.session_state.interview_data = {
        "questions": [],
        "answers": [],
        "current_q_index": 0,
        "waiting_for_answer": False,
        "interview_active": False,
        "user_name": "Candidate",
        "domain": "Healthcare Admin",
        "feedback_received": False,
        "feedbacks": []
    }

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
with st.sidebar:
    st.markdown("## 💬 Interview Bot")
    if st.button("➕ New Chat", use_container_width=True):
        save_current_session()
        st.rerun()
    st.markdown("### Chat History")
    if len(st.session_state.sessions) == 0:
        st.caption("No chats yet.")
    else:
        for idx, sess in enumerate(st.session_state.sessions):
            if st.button(f"{sess['name']} ({sess['created']})", key=f"chat_{idx}", use_container_width=True):
                st.session_state.current_session = sess
                st.session_state.interview_data = {
                    "questions": [],
                    "answers": [],
                    "current_q_index": 0,
                    "waiting_for_answer": False,
                    "interview_active": False,
                    "user_name": "Candidate",
                    "domain": "Healthcare Admin",
                    "feedback_received": False,
                    "feedbacks": []
                }
                st.rerun()

# -------------------------------------------------
# TOOLBAR
# -------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    if st.button("🎤 Interview Mode", use_container_width=True):
        st.session_state.mode = "interview"
        st.rerun()
with col2:
    if st.button("📚 Doubts Mode", use_container_width=True):
        st.session_state.mode = "doubts"
        st.rerun()
st.markdown("---")

# -------------------------------------------------
# DISPLAY CHAT
# -------------------------------------------------
for msg in st.session_state.current_session["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------------------------------------------------
# INTERVIEW MODE
# -------------------------------------------------
if st.session_state.mode == "interview":
    iv = st.session_state.interview_data

    if not iv["interview_active"]:
        with st.sidebar:
            st.markdown("### Start Interview")
            iv["user_name"] = st.text_input("Your Name", value=iv["user_name"])
            iv["domain"] = st.selectbox(
                "Domain",
                ["Healthcare Admin", "Hospitality", "Public Service", "Cybersecurity", "Software Testing"]
            )
            if st.button("▶️ Begin Interview", use_container_width=True):
                with st.spinner("Generating interview questions..."):
                    try:
                        resp = requests.post(
                            "http://127.0.0.1:8000/generate-question",
                            json={"domain": iv["domain"]},
                            timeout=120
                        )
                        data = resp.json()
                        iv["questions"] = data.get("questions", [])
                    except Exception as e:
                        st.error(f"Backend Error: {e}")
                        iv["questions"] = []

                if iv["questions"]:
                    iv["answers"] = []
                    iv["current_q_index"] = 0
                    iv["waiting_for_answer"] = True
                    iv["interview_active"] = True
                    iv["feedback_received"] = False

                    greeting = f"👋 Hello {iv['user_name']}!\n\nWelcome to your **{iv['domain']}** interview. Let's begin 🚀"
                    st.session_state.current_session["messages"].append({"role": "assistant", "content": greeting})
                    st.session_state.current_session["messages"].append({"role": "assistant", "content": iv["questions"][0]})
                    st.rerun()

    if iv["interview_active"]:
        if iv["waiting_for_answer"]:
            prompt = st.chat_input(f"Answer question {iv['current_q_index']+1}...")
        else:
            st.chat_input("Interview complete. Start a new chat.", disabled=True)

        if iv["waiting_for_answer"] and prompt:
            st.session_state.current_session["messages"].append({"role": "user", "content": prompt})
            iv["answers"].append(prompt)
            iv["current_q_index"] += 1

            if iv["current_q_index"] < len(iv["questions"]):
                next_q = iv["questions"][iv["current_q_index"]]
                st.session_state.current_session["messages"].append({"role": "assistant", "content": next_q})
                st.rerun()
            else:
                # All answers submitted → evaluate with a long timeout
                st.session_state.current_session["messages"].append({"role": "assistant", "content": "✅ Evaluating your answers..."})
                with st.spinner("🤖 AI is evaluating your responses (this may take a minute)..."):
                    try:
                        resp = requests.post(
                            "http://127.0.0.1:8000/evaluate-answers",
                            json={
                                "qa_list": [
                                    {"question": q, "answer": a}
                                    for q, a in zip(iv["questions"], iv["answers"])
                                ]
                            },
                            timeout=120   # 🔥 increased to 2 minutes
                        )
                        data = resp.json()
                        feedbacks = data.get("feedbacks", ["No feedback"] * len(iv["questions"]))
                    except Exception as e:
                        feedbacks = [f"⚠️ Evaluation error: {e}"] * len(iv["questions"])

                for i, (q, a, fb) in enumerate(zip(iv["questions"], iv["answers"], feedbacks)):
                    msg = f"""
### Question {i+1}
**Q:** {q}

**Your Answer:** {a}

**Feedback:** {fb}
"""
                    st.session_state.current_session["messages"].append({"role": "assistant", "content": msg})

                st.session_state.current_session["messages"].append({"role": "assistant", "content": "🎉 Interview completed! Download the report below."})
                iv["waiting_for_answer"] = False
                iv["feedback_received"] = True
                iv["feedbacks"] = feedbacks
                st.rerun()

    if iv.get("feedback_received"):
        report = f"Interview Report\n{'='*30}\nName: {iv['user_name']}\nDomain: {iv['domain']}\n\n"
        for i, (q, a, fb) in enumerate(zip(iv["questions"], iv["answers"], iv["feedbacks"])):
            report += f"Q{i+1}: {q}\nA{i+1}: {a}\nFeedback: {fb}\n\n"

        st.download_button(
            label="📥 Download Report",
            data=report,
            file_name=f"interview_report_{iv['user_name']}_{iv['domain']}.txt",
            mime="text/plain"
        )

# -------------------------------------------------
# DOUBTS MODE (CORRECTED)
# -------------------------------------------------
elif st.session_state.mode == "doubts":
    prompt = st.chat_input("Ask any doubt...")
    if prompt:
        st.session_state.current_session["messages"].append({"role": "user", "content": prompt})
        with st.spinner("Looking for an answer..."):
            try:
                resp = requests.post(
                    "http://127.0.0.1:8000/ask-doubt",
                    json={"question": prompt},
                    timeout=120
                )
                data = resp.json()
                answer = data.get("answer", "No response received.")
            except Exception as e:
                answer = f"⚠️ Error: {e}"
        st.session_state.current_session["messages"].append({"role": "assistant", "content": answer})
        st.rerun()