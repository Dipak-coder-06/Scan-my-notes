"""
app.py — Scan My Notes
-----------------------------
Productivity & Study Suite featuring:
1. Workspace with Chat 
2. Persistent Session Management (Load/Rename/Delete)
3. Task List & Pomodoro Tracker
4. MCQ Generator & Gamified Quiz
5. PDF Export & Dark/Light mode toggle
"""
import os
import tempfile
import json
import uuid
from typing import List, Dict, Any
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Scan My Notes",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State Init ────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "current_page": "Workspace",
        # Workspace
        "session_id": str(uuid.uuid4()),
        "chat_history": [],
        "doc_processed": False,
        "doc_name": None,
        "chunk_count": 0,
        "page_count": 0,
        # Global History
        "global_history": {}, # UUID -> {title, timestamp, doc_name, chunks, chat_history}
        # Tasks & Pomodoro
        "todos": [
            {"id": str(uuid.uuid4()), "text": "Review Chapter 3", "done": False, "pomodoros": 0}
        ],
        "active_pomodoro": None, # Task ID
        "pomodoro_end_time": None,
        # Quiz
        "mcqs": [],
        "quiz_active": False,
        "quiz_idx": 0,
        "quiz_score": 0,
        "quiz_answers": [], # selected options
        # Theme
        "theme": "dark"
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ── Persistent Storage ────────────────────────────────────────────────────────
HISTORY_FILE = "scan_my_notes_history.json"
TODOS_FILE = "scan_my_notes_todos.json"

def save_data():
    with open(HISTORY_FILE, "w") as f:
        json.dump(st.session_state.global_history, f)
    with open(TODOS_FILE, "w") as f:
        json.dump(st.session_state.todos, f)

def load_data():
    if os.path.exists(HISTORY_FILE) and not st.session_state.global_history:
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Migration: Reset history if old list schema is detected
                    st.session_state.global_history = {}
                else:
                    st.session_state.global_history = data
        except: pass
    if os.path.exists(TODOS_FILE) and len(st.session_state.todos) == 1:
        try:
            with open(TODOS_FILE, "r") as f:
                st.session_state.todos = json.load(f)
        except: pass

load_data()

def archive_current_session():
    if st.session_state.chat_history:
        sid = st.session_state.session_id
        if sid not in st.session_state.global_history:
            title = f"Session {datetime.now().strftime('%b %d, %H:%M')}"
        else:
            title = st.session_state.global_history[sid]["title"]

        st.session_state.global_history[sid] = {
            "title": title,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "doc_name": st.session_state.doc_name,
            "chunks": st.session_state.chunk_count,
            "chat_history": st.session_state.chat_history
        }
        save_data()

# ── Styles (Dark/Light) ───────────────────────────────────────────────────────
css_dark = """
    background: linear-gradient(135deg, #09090b 0%, #18181b 50%, #09090b 100%); color: #e4e4e7;
    --card-bg: rgba(39, 39, 42, 0.4); --border: rgba(255,255,255,0.08); 
    --text: #e4e4e7; --text-muted: #a1a1aa;
"""
css_light = """
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #f8fafc 100%); color: #0f172a;
    --card-bg: rgba(255, 255, 255, 0.7); --border: rgba(0,0,0,0.1); 
    --text: #0f172a; --text-muted: #475569;
"""

theme_css = css_light if st.session_state.theme == "light" else css_dark

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

* {{ font-family: 'Outfit', sans-serif; }}

.stApp {{ {theme_css} }}

[data-testid="stSidebar"] {{
    background: var(--card-bg);
    backdrop-filter: blur(12px);
    border-right: 1px solid var(--border);
}}
.glass-card {{
    background: var(--card-bg);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;
    color: var(--text);
}}
.metric-value {{ font-size: 1.8rem; font-weight: 600; color: var(--text); }}
.metric-label {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}

.chat-user {{
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 12px 12px 4px 12px;
    padding: 1rem 1.2rem; margin: 1rem 0 1rem auto;
    color: var(--text); max-width: 85%;
}}
.chat-assistant {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px 12px 12px 4px;
    padding: 1rem 1.2rem; margin: 1rem 0;
    color: var(--text); max-width: 90%; line-height: 1.6;
}}
.citation-footer {{
    background: rgba(0,0,0,0.1); border-left: 2px solid #60a5fa;
    padding: 0.75rem 1rem; margin-top: 1rem; border-radius: 4px 8px 8px 4px;
    font-size: 0.85rem; font-family: 'Fira Code', monospace; color: #60a5fa;
}}
.badge {{ display: inline-flex; align-items: center; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
.hero-title {{ font-size: 2.5rem; font-weight: 700; background: linear-gradient(to right, #60a5fa, #a78bfa, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.2rem; }}
.hero-subtitle {{ color: var(--text-muted); font-weight: 400; font-size: 1rem; }}
.todo-text {{ color: var(--text); }}
.todo-done {{ color: var(--text-muted); text-decoration: line-through; }}
</style>
""", unsafe_allow_html=True)


# ── Utilities ─────────────────────────────────────────────────────────────────
def nav_button(label: str, target: str):
    if st.button(label, key=f"nav_{target}", use_container_width=True):
        st.session_state.current_page = target
        st.rerun()

def render_assistant_message(msg: Dict[str, Any]):
    conf = msg.get("confidence", 0)
    conf_label = msg.get("confidence_label", "")
    conf_color = msg.get("confidence_color", "#94a3b8")
    citations = msg.get("citations", [])
    
    badge = f'<span class="badge" style="background:{conf_color}22; color:{conf_color}; border:1px solid {conf_color}44;">🎯 {conf}% {conf_label}</span>'
    content = msg["content"].replace("\n", "<br>")
    
    cite_html = ""
    if citations and not msg.get("no_information"):
        lines = "".join(f'<div>[{c["citation_index"]}] {c["label"]}</div>' for c in citations)
        cite_html = f'<div class="citation-footer">📍 <strong>Spatial Anchors</strong><br>{lines}</div>'
        
    st.markdown(
        f'<div class="chat-assistant">📝 {badge}<div style="margin:1rem 0;">{content}</div>{cite_html}</div>',
        unsafe_allow_html=True
    )

def _run_ingestion(uploaded_file):
    gcp_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    placeholder_values = {"", "path/to/your/service-account-key.json", "path/to/your-key.json"}
    if gcp_key_path in placeholder_values or not os.path.exists(gcp_key_path):
        st.error(
            f"❌ GCP credentials not configured. "
            f"Set GOOGLE_APPLICATION_CREDENTIALS in your `.env` file to the path of your service account JSON key."
        )
        st.stop()
    import fitz
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    doc = fitz.open(tmp_path)
    page_count = len(doc)
    doc.close()

    status = st.empty()
    bar = st.progress(0)
    try:
        from pipeline.ingest import ingest_pdf
        status.markdown("⏳ Extracting coordinates...")
        words = ingest_pdf(tmp_path, progress_callback=lambda c, t: bar.progress(int((c/t)*33)))
        from pipeline.chunker import chunk_words
        status.markdown("⏳ Structuring chunks...")
        chunks = chunk_words(words)
        bar.progress(66)
        from pipeline.embedder import store_chunks, clear_collection
        status.markdown("⏳ Vectorizing...")
        clear_collection()
        
        # Save raw chunks to session state so MCQ generator can use it
        st.session_state.raw_chunks = chunks 

        stored = store_chunks(chunks, progress_callback=lambda c, t: bar.progress(66 + int((c/t)*34)))

        st.session_state.doc_processed = True
        st.session_state.doc_name = uploaded_file.name
        st.session_state.chunk_count = stored
        st.session_state.page_count = page_count
        st.session_state.session_id = str(uuid.uuid4())
        
        status.empty(); bar.empty()
        st.success("✅ Ingestion Complete!")
        st.rerun()
    except Exception as e:
        status.empty(); bar.empty()
        st.error(f"❌ Ingestion failed: {str(e)}")
    finally:
        os.unlink(tmp_path)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    c_img, c_theme = st.columns([4,1])
    c_theme.button("🌗", key="theme_toggle", on_click=lambda: st.session_state.update(theme="light" if st.session_state.theme == "dark" else "dark"))
    
    st.markdown("""
    <div style="text-align:center; padding:0 0 1rem 0;">
        <span style="font-size:3rem; line-height:1;">📝</span>
        <h3 style="color:#60a5fa; margin:0; font-size:1.4rem;">Scan My Notes</h3>
    </div>
    """, unsafe_allow_html=True)
    
    nav_button("📄 Workspace", "Workspace")
    nav_button("🗂️ Chat Sessions", "History")
    nav_button("✅ To-Do & Pomodoro", "Tasks")
    nav_button("🎯 MCQ Quiz Generator", "Quiz")
    st.divider()

    if st.session_state.doc_processed:
        st.markdown(
            f'<div class="glass-card" style="padding:1rem; margin-bottom:0.5rem">'
            f'<div style="color:#4ade80; font-size:0.7rem; font-weight:600;">ACTIVE DOCUMENT</div>'
            f'<div style="font-size:0.9rem; overflow:hidden; white-space:nowrap;">{st.session_state.doc_name}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        col1, col2 = st.columns(2)
        if col1.button("🗑️ Eject", use_container_width=True):
            archive_current_session()
            st.session_state.doc_processed = False
            st.session_state.chat_history = []
            st.session_state.mcqs = []
            st.session_state.quiz_active = False
            from pipeline.embedder import clear_collection
            clear_collection()
            st.rerun()
        if col2.button("✨ New", type="primary", use_container_width=True):
            archive_current_session()
            st.session_state.doc_processed = False
            st.session_state.chat_history = []
            st.session_state.doc_name = None
            st.session_state.session_id = str(uuid.uuid4())
            from pipeline.embedder import clear_collection
            clear_collection()
            st.rerun()


# ── Pages ─────────────────────────────────────────────────────────────────────

if st.session_state.current_page == "Workspace":
    st.markdown('<div class="hero-title">Knowledge Workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Chat with your documents securely.</div><br>', unsafe_allow_html=True)

    if not st.session_state.doc_processed:
        st.markdown('<div class="glass-card" style="text-align:center; padding:3rem;">', unsafe_allow_html=True)
        st.markdown("### 📥 Import Document")
        uploaded = st.file_uploader("", type=["pdf"], label_visibility="collapsed")
        if uploaded and st.button("Initialize Pipeline →", type="primary"):
            _run_ingestion(uploaded)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="glass-card"><div class="metric-value">{st.session_state.page_count}</div><div class="metric-label">Pages</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="glass-card"><div class="metric-value">{st.session_state.chunk_count}</div><div class="metric-label">Nodes</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="glass-card"><div class="metric-value">Local</div><div class="metric-label">Privacy</div></div>', unsafe_allow_html=True)
        
        with c4:
            if st.session_state.chat_history:
                from modules.pdf_exporter import export_qa_to_pdf
                pdf_bytes = export_qa_to_pdf(st.session_state.doc_name, st.session_state.chat_history)
                st.write("")
                st.download_button("📥 Export Q&A to PDF", data=pdf_bytes, file_name=f"Q&A_{st.session_state.doc_name}.pdf", mime="application/pdf", use_container_width=True)

        st.markdown("---")
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                render_assistant_message(msg)
                
        with st.form("chat_form", clear_on_submit=True):
            cols = st.columns([5,1])
            query = cols[0].text_input("Ask...", label_visibility="collapsed")
            if cols[1].form_submit_button("Query", use_container_width=True) and query.strip():
                from pipeline.retriever import hybrid_search
                from pipeline.generator import generate_answer
                st.session_state.chat_history.append({"role": "user", "content": query})
                with st.spinner("🧠 Searching..."):
                    retrieved = hybrid_search(query, top_k=5)
                    res = generate_answer(query, retrieved)
                st.session_state.chat_history.append({
                    "role": "assistant", "content": res["answer"],
                    "confidence": res["confidence"], "confidence_label": res["confidence_label"],
                    "confidence_color": res["confidence_color"], "citations": res["citations"],
                    "no_information": res.get("no_information", False)
                })
                archive_current_session()
                st.rerun()

elif st.session_state.current_page == "History":
    st.markdown('<div class="hero-title">Chat Sessions</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Manage and reload your previous workspaces.</div><br>', unsafe_allow_html=True)
    
    if not st.session_state.global_history:
        st.info("No saved sessions.")
    else:
        for sid, record in list(st.session_state.global_history.items()):
            with st.expander(f"📁 {record['title']} ({record.get('doc_name','Unknown')}) - {record['timestamp']}"):
                c1, c2, c3 = st.columns([1, 1, 4])
                if c1.button("♻️ Load Session", key=f"load_{sid}"):
                    st.session_state.session_id = sid
                    st.session_state.chat_history = record["chat_history"]
                    st.session_state.doc_name = record["doc_name"]
                    st.session_state.doc_processed = True
                    st.session_state.current_page = "Workspace"
                    st.rerun()
                if c2.button("🗑️ Delete", key=f"del_{sid}"):
                    del st.session_state.global_history[sid]
                    save_data()
                    st.rerun()
                
                new_title = st.text_input("Rename Session", value=record["title"], key=f"rn_{sid}", label_visibility="collapsed")
                if new_title != record["title"]:
                    st.session_state.global_history[sid]["title"] = new_title
                    save_data()
                    
                st.markdown("---")
                user_msgs = [m for m in record["chat_history"] if m["role"] == "user"]
                for i, m in enumerate(user_msgs[:3]):
                    st.markdown(f"**Q{i+1}:** {m['content']}")
                if len(user_msgs) > 3:
                    st.markdown("*...and more*")


elif st.session_state.current_page == "Tasks":
    st.markdown('<div class="hero-title">To-Do & Pomodoro</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Track tasks and use the built-in timer.</div><br>', unsafe_allow_html=True)
    
    # ── Interactive JS Pomodoro Timer ──
    import streamlit.components.v1 as components
    components.html("""
    <div style="background: rgba(39, 39, 42, 0.4); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; text-align: center; color: white; font-family: sans-serif;">
        <h1 id="timeDisplay" style="font-size: 3.5rem; margin: 0; padding: 10px; font-weight: 700; letter-spacing: 5px;">25:00</h1>
        <div style="margin-top: 15px;">
            <button onclick="startTimer(25)" style="background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 1rem; margin: 0 5px; font-weight: 600;">🍅 25m Focus</button>
            <button onclick="startTimer(5)" style="background: #10b981; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 1rem; margin: 0 5px; font-weight: 600;">☕ 5m Break</button>
            <button onclick="startTimer(15)" style="background: #8b5cf6; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 1rem; margin: 0 5px; font-weight: 600;">🛋️ 15m Break</button>
            <button onclick="stopTimer()" style="background: #ef4444; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 1rem; margin: 0 5px; font-weight: 600;">⏹️ Stop</button>
        </div>
        <script>
            let interval = null;
            function updateDisplay(seconds) {
                const m = Math.floor(seconds / 60).toString().padStart(2, '0');
                const s = (seconds % 60).toString().padStart(2, '0');
                document.getElementById('timeDisplay').innerText = `${m}:${s}`;
            }
            function startTimer(minutes) {
                clearInterval(interval);
                let seconds = minutes * 60;
                updateDisplay(seconds);
                interval = setInterval(() => {
                    seconds--;
                    if (seconds <= 0) {
                        clearInterval(interval);
                        updateDisplay(0);
                        alert(minutes === 25 ? "🍅 Pomodoro finished! Log your session below." : "☕ Break finished! Back to work.");
                    } else {
                        updateDisplay(seconds);
                    }
                }, 1000);
            }
            function stopTimer() {
                clearInterval(interval);
                document.getElementById('timeDisplay').innerText = "00:00";
            }
        </script>
    </div>
    """, height=220)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    with st.form("add_task", clear_on_submit=True):
        cols = st.columns([4,1])
        new_task = cols[0].text_input("New Task", label_visibility="collapsed")
        if cols[1].form_submit_button("Add Task") and new_task:
            st.session_state.todos.append({"id": str(uuid.uuid4()), "text": new_task, "done": False, "pomodoros": 0})
            save_data()
            st.rerun()
            
    st.write("")
    for i, t in enumerate(st.session_state.todos):
        c1, c2, c3, c4 = st.columns([0.5, 6, 2, 1])
        
        # Checkbox
        done = c1.checkbox("", value=t["done"], key=f"chk_{t['id']}")
        if done != t["done"]:
            st.session_state.todos[i]["done"] = done
            save_data()
            st.rerun()
            
        # Text
        t_class = "todo-done" if t["done"] else "todo-text"
        c2.markdown(f'<div class="{t_class}" style="padding-top:0.4rem;">{t["text"]} (🍅 {t.get("pomodoros",0)})</div>', unsafe_allow_html=True)
        
        # Pomodoro Log Button
        if c3.button("⏱️ Log 25m", key=f"pom_{t['id']}", help="Log a completed Pomodoro session"):
            st.session_state.todos[i]["pomodoros"] = st.session_state.todos[i].get("pomodoros", 0) + 1
            save_data()
            st.success(f"Great job! Added 1 Pomodoro to '{t['text']}'")
            st.rerun()
            
        # Delete Button
        if c4.button("✕", key=f"del_{t['id']}"):
            st.session_state.todos.pop(i)
            save_data()
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)


elif st.session_state.current_page == "Quiz":
    st.markdown('<div class="hero-title">MCQ Quiz Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Generate interactive Quizzes directly from PDF facts.</div><br>', unsafe_allow_html=True)

    if not st.session_state.doc_processed:
        st.warning("Upload a document in the Workspace first.")
    else:
        # Export logic
        if st.session_state.mcqs:
            from modules.pdf_exporter import export_mcqs_to_pdf
            pdf_bytes = export_mcqs_to_pdf(st.session_state.doc_name, st.session_state.mcqs)
            colA, colB = st.columns([1,4])
            colA.download_button("📥 Download PDF Quiz", data=pdf_bytes, file_name="MCQ_Quiz.pdf", mime="application/pdf", use_container_width=True)

        if not st.session_state.quiz_active:
            if not st.session_state.mcqs:
                if st.button("🚀 Generate MCQs (10-15 Questions)", type="primary"):
                    with st.spinner("Generating High-Quality MCQs with llama3.2... This takes 10-20 seconds."):
                        from modules.mcq_generator import generate_mcqs
                        # We stored `raw_chunks` during ingestion specifically for this
                        chunks = st.session_state.get("raw_chunks", [])
                        mcqs = generate_mcqs(chunks)
                        if mcqs:
                            st.session_state.mcqs = mcqs
                            st.session_state.quiz_active = True
                            st.session_state.quiz_idx = 0
                            st.session_state.quiz_score = 0
                            st.session_state.quiz_answers = []
                            st.rerun()
                        else:
                            st.error("Failed to generate MCQs. Please check Ollama logs.")
            else:
                st.success(f"Ready! Generated {len(st.session_state.mcqs)} questions.")
                col1, col2 = st.columns(2)
                if col1.button("🎮 Start Interactive Quiz", type="primary"):
                    st.session_state.quiz_active = True
                    st.session_state.quiz_idx = 0
                    st.session_state.quiz_score = 0
                    st.session_state.quiz_answers = []
                    st.rerun()
                if col2.button("♻️ Regenerate Quiz"):
                    st.session_state.mcqs = []
                    st.rerun()
        else:
            # Active Quiz View
            st.button("← Exit Quiz", on_click=lambda: st.session_state.update(quiz_active=False))
            st.markdown("---")
            
            mcqs = st.session_state.mcqs
            idx = st.session_state.quiz_idx
            
            if idx < len(mcqs):
                q = mcqs[idx]
                st.progress((idx) / len(mcqs))
                st.markdown(f"#### Question {idx+1} of {len(mcqs)}")
                st.markdown(f"### {q['question']}")
                
                # Check if answered
                if len(st.session_state.quiz_answers) == idx:
                    # Not answered yet
                    st.write("Select an answer:")
                    for opt in q["options"]:
                        if st.button(opt, use_container_width=True):
                            st.session_state.quiz_answers.append(opt)
                            if opt == q["correct_answer"]:
                                st.session_state.quiz_score += 1
                            st.rerun()
                else:
                    # Answered, show feedback
                    user_ans = st.session_state.quiz_answers[idx]
                    is_correct = user_ans == q["correct_answer"]
                    
                    if is_correct:
                        st.success(f"**Correct!** You chose: {user_ans}")
                    else:
                        st.error(f"**Incorrect.** You chose: {user_ans}. Correct was: {q['correct_answer']}")
                        
                    st.info(f"**Explanation:** {q['explanation']}")
                    
                    if st.button("Next Question →", type="primary"):
                        st.session_state.quiz_idx += 1
                        st.rerun()
            else:
                # Quiz complete
                st.balloons()
                st.markdown("## 🏆 Quiz Complete!")
                st.markdown(f"### Final Score: {st.session_state.quiz_score} / {len(mcqs)}")
                pct = (st.session_state.quiz_score / len(mcqs)) * 100
                if pct == 100: st.success("Perfect score! Flawless victory.")
                elif pct >= 70: st.info("Great job! You know this material well.")
                else: st.warning("Good start! Review the generated PDF for more practice.")
                
                if st.button("Retake Quiz", type="primary"):
                    st.session_state.quiz_idx = 0
                    st.session_state.quiz_score = 0
                    st.session_state.quiz_answers = []
                    st.rerun()
