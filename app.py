"""Grounds AI: a local chatbot that answers questions about spent coffee grounds
using PDFs that the user uploads.

How it works (Retrieval-Augmented Generation, RAG):
1. The user uploads a PDF on the Documents page.
2. The app reads the text page by page (PyMuPDF) and cuts it into short passages.
3. Each passage is turned into a vector (embedding) by a local Ollama model and
   saved in a small SQLite database.
4. When the user asks a question, the question is also turned into a vector.
   The most similar passages are found and sent to the chat model together with
   the question, so the answer is based on our local documents.
Everything runs on the user's own computer through Ollama.
"""

import json
import math
import os
import sqlite3
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
import requests
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gemma3:1b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "knowledge.sqlite3"

PASSAGE_WORDS = 200    # words per passage
PASSAGE_OVERLAP = 40   # words shared between neighbouring passages
TOP_K = 4              # passages sent to the model for each question
MIN_SCORE = 0.30       # ignore passages that are not similar enough

SYSTEM_PROMPT = (
    "You are Grounds AI, a helpful assistant about spent coffee grounds: how cafes "
    "in Bangkok can collect, reuse and turn them into products such as body scrubs, "
    "and the science behind it. Answer in simple, clear English. "
    "Use ONLY the document passages below. After each fact, cite the source like "
    "[filename, p. N]. If the passages do not contain the answer, say "
    "'My documents do not cover this.' Never make up sources."
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "grounds-ai-dev-key")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB per upload


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE IF NOT EXISTS documents (
               filename TEXT PRIMARY KEY,
               pages INTEGER NOT NULL,
               passages INTEGER NOT NULL,
               status TEXT NOT NULL,
               message TEXT NOT NULL DEFAULT '')"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS passages (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               filename TEXT NOT NULL,
               page INTEGER NOT NULL,
               text TEXT NOT NULL,
               vector TEXT NOT NULL)"""
    )
    return db


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------
def embed(texts):
    """Return one embedding vector for each text."""
    vectors = []
    # Send in small batches so large PDFs do not time out.
    for i in range(0, len(texts), 32):
        batch = texts[i:i + 32]
        r = requests.post(f"{OLLAMA_URL}/api/embed",
                          json={"model": EMBED_MODEL, "input": batch}, timeout=180)
        r.raise_for_status()
        result = r.json().get("embeddings")
        if not isinstance(result, list) or len(result) != len(batch):
            raise ValueError("Unexpected embedding response from Ollama.")
        vectors.extend(result)
    return vectors


def chat_with_model(messages):
    r = requests.post(f"{OLLAMA_URL}/api/chat",
                      json={"model": CHAT_MODEL, "messages": messages, "stream": False},
                      timeout=300)
    r.raise_for_status()
    content = (r.json().get("message") or {}).get("content")
    if not isinstance(content, str):
        raise ValueError("Unexpected chat response from Ollama.")
    return content


# ---------------------------------------------------------------------------
# Reading and indexing PDFs
# ---------------------------------------------------------------------------
def split_into_passages(text):
    words = text.split()
    passages, start = [], 0
    step = PASSAGE_WORDS - PASSAGE_OVERLAP
    while start < len(words):
        chunk = " ".join(words[start:start + PASSAGE_WORDS])
        if len(chunk) > 40:  # skip tiny scraps such as page numbers
            passages.append(chunk)
        start += step
    return passages


def index_pdf(path):
    """Read a PDF, embed its passages and save them. Returns (status, message)."""
    items = []
    with fitz.open(path) as pdf:
        page_count = pdf.page_count
        for page_no, page in enumerate(pdf, start=1):
            for passage in split_into_passages(page.get_text("text")):
                items.append((page_no, passage))

    db = get_db()
    db.execute("DELETE FROM passages WHERE filename = ?", (path.name,))
    if not items:
        status, message = "no_text", "No readable text (it may be a scanned PDF)."
    else:
        try:
            vectors = embed([text for _, text in items])
            db.executemany(
                "INSERT INTO passages (filename, page, text, vector) VALUES (?, ?, ?, ?)",
                [(path.name, page, text, json.dumps(vec))
                 for (page, text), vec in zip(items, vectors)],
            )
            status, message = "ready", ""
        except (requests.RequestException, ValueError) as error:
            status, message = "error", f"Could not create embeddings: {error}"[:300]
    saved = len(items) if status == "ready" else 0
    db.execute("INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?)",
               (path.name, page_count, saved, status, message))
    db.commit()
    db.close()
    return status, message


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def find_passages(question):
    query = embed([question])[0]
    db = get_db()
    rows = db.execute("SELECT filename, page, text, vector FROM passages").fetchall()
    db.close()
    scored = [(cosine(query, json.loads(row["vector"])), row) for row in rows]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [(score, row) for score, row in scored[:TOP_K] if score >= MIN_SCORE]


def list_documents():
    db = get_db()
    docs = [dict(row) for row in db.execute("SELECT * FROM documents ORDER BY filename")]
    db.close()
    return docs


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.get("/")
def home():
    return render_template("index.html", docs=list_documents(), model=CHAT_MODEL)


@app.get("/documents")
def documents():
    return render_template("documents.html", docs=list_documents())


@app.post("/documents/upload")
def upload():
    file = request.files.get("pdf")
    if not file or not file.filename:
        flash("Please choose a PDF file.", "error")
        return redirect(url_for("documents"))
    name = secure_filename(file.filename)
    if not name.lower().endswith(".pdf"):
        flash("Only PDF files can be uploaded.", "error")
        return redirect(url_for("documents"))

    UPLOAD_DIR.mkdir(exist_ok=True)
    path = UPLOAD_DIR / name
    file.save(path)
    try:
        status, message = index_pdf(path)
    except Exception as error:  # damaged or unreadable PDF
        path.unlink(missing_ok=True)
        flash(f"Could not read {name}: {error}", "error")
        return redirect(url_for("documents"))

    if status == "ready":
        flash(f"{name} is ready to use.", "success")
    else:
        flash(f"{name} was saved, but: {message}", "error")
    return redirect(url_for("documents"))


@app.post("/documents/delete/<name>")
def delete(name):
    name = secure_filename(name)
    (UPLOAD_DIR / name).unlink(missing_ok=True)
    db = get_db()
    db.execute("DELETE FROM passages WHERE filename = ?", (name,))
    db.execute("DELETE FROM documents WHERE filename = ?", (name,))
    db.commit()
    db.close()
    flash(f"Deleted {name}.", "success")
    return redirect(url_for("documents"))


@app.errorhandler(413)
def too_large(_error):
    flash("That file is too large. The limit is 20 MB.", "error")
    return redirect(url_for("documents"))


# ---------------------------------------------------------------------------
# Chat API
# ---------------------------------------------------------------------------
@app.post("/api/chat")
def api_chat():
    data = request.get_json(silent=True) or {}
    history = data.get("messages")
    use_docs = data.get("use_documents", True)
    if not isinstance(history, list) or not history:
        return jsonify(error="No message was sent."), 400

    # Keep only plain user/assistant text so nothing else reaches Ollama.
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in history[-12:]
        if isinstance(m, dict) and m.get("role") in ("user", "assistant")
        and isinstance(m.get("content"), str)
    ]
    if not messages or messages[-1]["role"] != "user":
        return jsonify(error="The last message must come from the user."), 400
    question = messages[-1]["content"]

    sources = []
    try:
        if use_docs:
            found = find_passages(question) if list_documents() else []
            if found:
                context = "\n\n".join(
                    f"[{row['filename']}, p. {row['page']}]\n{row['text']}" for _, row in found)
                sources = [{"filename": row["filename"], "page": row["page"],
                            "score": round(score, 2)} for score, row in found]
            else:
                context = "(No matching passages were found in the uploaded documents.)"
            messages.insert(0, {"role": "system",
                                "content": SYSTEM_PROMPT + "\n\nDOCUMENT PASSAGES:\n" + context})
        answer = chat_with_model(messages)
    except requests.RequestException:
        return jsonify(error=f"Could not reach Ollama at {OLLAMA_URL}. Is it running, and are "
                             f"{CHAT_MODEL} and {EMBED_MODEL} downloaded?"), 502
    except ValueError as error:
        return jsonify(error=str(error)), 502

    return jsonify(answer=answer, sources=sources)


if __name__ == "__main__":
    UPLOAD_DIR.mkdir(exist_ok=True)
    get_db().close()
    app.run(host="127.0.0.1", port=5000, debug=False)
