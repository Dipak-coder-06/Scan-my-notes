<div align="center">

# 🛡️ Ironclad Scholar Pro

**High-Precision, Privacy-First Document Intelligence for Handwritten & Typed Notes**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=for-the-badge&logo=ollama)](https://ollama.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange?style=for-the-badge)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

*Chat with your documents. Generate quizzes. Export everything. No cloud, no subscription — just your data, your machine.*

</div>

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔍 **Intelligent Q&A** | Ask questions about your PDFs — answers are grounded in your document, never hallucinated |
| 🧠 **Hybrid Search** | BM25 keyword search + semantic vector search fused by Reciprocal Rank Fusion (RRF) |
| 📍 **Spatial Citations** | Every answer links back to exact page numbers and section titles |
| 🎯 **Confidence Scoring** | 0-100% confidence score computed from retrieval quality signals |
| 🔒 **Veracity Guardrails** | Strict grounding system prompt; refuses to answer beyond document content |
| 🎮 **MCQ Quiz Generator** | Auto-generate 10–15 multiple-choice questions from any document |
| 📥 **PDF Export** | Download your Q&A session or quiz as a formatted PDF report |
| ✅ **Task Manager** | Built-in to-do list with Pomodoro timer (25/5/15 min intervals) |
| 🗂️ **Session History** | Persistent chat sessions — load, rename, delete past workspace sessions |
| 🌗 **Dark / Light Mode** | Toggle themes with one click |

---

## 🏗️ System Architecture

```
PDF Upload
    │
    ▼
Google Cloud Vision API  ──► Word-level OCR with (x, y, page) coordinates
    │
    ▼
Smart Chunker  ──► Section detection, table detection (Visual Parser), gap-splitting
    │
    ▼
Ollama nomic-embed-text  ──► 768-dim dense embeddings
    │
    ▼
ChromaDB (local)  ──► Persistent cosine-similarity vector store
    │
    ▼ (at query time)
Hybrid Search
    ├── Semantic: ChromaDB ANN query
    ├── Keyword:  BM25Okapi over full corpus
    └── Fusion:   Reciprocal Rank Fusion (RRF, k=60)
    │
    ▼
Ollama llama3.2 (T=0.0)  ──► Grounded answer generation
    │
    ▼
Veracity Guard  ──► Confidence scoring + hallucination suppression
    │
    ▼
Citation Engine  ──► "📄 Page 3 · Section: Thermodynamics"
```

---

## ⚡ Quick Start

### Prerequisites

1. **Python 3.10+**
2. **[Ollama](https://ollama.com/)** (local LLM runner)
3. **Google Cloud Vision API** credentials (for OCR)

### Step 1 — Install Ollama Models

```bash
# Pull the embedding + generation models
ollama pull nomic-embed-text
ollama pull llama3.2
```

### Step 2 — Google Cloud Vision Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → enable the **Cloud Vision API**
3. Create a **Service Account** → download the JSON key
4. Copy the key file somewhere safe (e.g., `~/.config/ironclad/gcp-key.json`)

### Step 3 — Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/Ironclad-Scholar.git
cd Ironclad-Scholar

# Copy the environment template
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/your-gcp-key.json
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3.2
TOP_K_CHUNKS=5
CHROMA_PERSIST_DIR=./chroma_db
```

### Step 4 — Install Dependencies & Run

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run app.py
```

Open **http://localhost:8501** in your browser. 🎉

---

## 📁 Project Structure

```
Ironclad-Scholar/
│
├── app.py                       # 🖥️  Streamlit UI — all 4 pages
│
├── pipeline/                    # ⚙️  Core RAG pipeline
│   ├── __init__.py
│   ├── ingest.py                #   PDF → Google Vision OCR → word objects
│   ├── chunker.py               #   Smart section chunking with table detection
│   ├── embedder.py              #   nomic-embed-text → ChromaDB  
│   ├── retriever.py             #   Hybrid BM25 + vector + RRF search
│   └── generator.py            #   llama3.2 grounded answer generation
│
├── modules/                     # 🧩  Intelligence modules
│   ├── __init__.py
│   ├── citation_engine.py       #   Spatial "Page X, Section Y" citations
│   ├── veracity_guard.py        #   Confidence scoring & hallucination guardrails
│   ├── visual_parser.py         #   Handwritten table → Markdown conversion
│   ├── mcq_generator.py         #   AI-powered MCQ quiz generation
│   └── pdf_exporter.py          #   Q&A & quiz → downloadable PDF
│
├── requirements.txt
├── .env.example                 # ← copy this to .env and fill in your keys
└── .gitignore
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | *(required)* | Absolute path to your GCP service account JSON key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model (768-dim) |
| `OLLAMA_LLM_MODEL` | `llama3.2` | LLM used for answer generation |
| `TOP_K_CHUNKS` | `5` | Number of chunks retrieved per query |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Local persistent vector store path |

---

## 🔒 Privacy & Offline Guarantee

| Stage | Network |
|---|---|
| **PDF Upload → OCR** | ☁️ Google Vision API (internet required) |
| **Chunking** | 💻 100% local |
| **Embedding** | 💻 100% local via Ollama |
| **Vector Storage** | 💻 100% local via ChromaDB |
| **Q&A / Quiz** | 💻 100% local via Ollama |

> After the initial OCR step, **all AI inference happens on your machine**. Your notes never leave after ingestion.

---

## 🛠️ How It Works

### 1. Ingestion Pipeline
PDFs are rendered page-by-page at 200 DPI, then sent to Google Vision's `document_text_detection` API. This returns word-level bounding boxes `(x, y, w, h)` and confidence scores — essential for handwriting and complex layouts.

### 2. Smart Chunking
Words are sorted by reading order (page → y → x) and split into semantic groups based on:
- **Page breaks** — each page starts a new group
- **Vertical gaps** — whitespace > 45px signals a new section
- **Header words** — tall bounding boxes (h ≥ 28px) indicate section titles
- **Table regions** — consistent column alignment → converted to Markdown before embedding
- **Diagram labels** — sparse word regions tagged as `[Diagram Labels]: ...`

### 3. Hybrid Retrieval
At query time, two search strategies run in parallel:
- **Semantic**: nomic-embed-text embeds the query → ChromaDB ANN (cosine) retrieves top candidates
- **Keyword**: BM25Okapi scores all documents against the tokenized query
- **Fusion**: Reciprocal Rank Fusion (RRF, k=60) merges both ranked lists for optimal recall

### 4. Veracity Guardrails
A strict system prompt forces llama3.2 to ONLY answer from retrieved context. A composite confidence score (60% cosine similarity + 25% BM25 + 15% coverage) is computed. If confidence < 15%, the answer is suppressed and replaced with an explicit "I don't have enough information" message.

### 5. Spatial Citations
Each retrieved chunk carries its page number and section title as metadata. After generation, `citation_engine.py` formats these into human-readable anchors displayed below every answer.

---

## 🧪 Running Tests

```bash
python test_pipeline.py
```

The test script verifies the chunker, embedder, retriever, and generator without a Streamlit UI.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">
Built with ❤️ for students, researchers, and lifelong learners.
</div>
