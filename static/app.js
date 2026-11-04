// Chat page logic: keeps the conversation in the browser and sends it to Flask.
const STORAGE_KEY = "grounds-ai-chat";
const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("question");
const sendBtn = document.getElementById("send");
const useDocs = document.getElementById("use-docs");

let history = [];
try {
  history = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
} catch (e) {
  history = [];
}

function save() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(history)); } catch (e) { /* ignore */ }
}

function addBubble(role, text, sources) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  if (sources && sources.length) {
    const list = document.createElement("div");
    list.className = "sources";
    list.textContent = "Sources: " + sources.map(s => `${s.filename} (p. ${s.page})`).join(", ");
    div.appendChild(list);
  }
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

history.forEach(m => addBubble(m.role, m.content, m.sources));

async function send() {
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  history.push({ role: "user", content: text });
  addBubble("user", text);
  save();

  sendBtn.disabled = true;
  const waiting = addBubble("assistant thinking", "Thinking…");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: history.map(m => ({ role: m.role, content: m.content })),
        use_documents: useDocs.checked,
      }),
    });
    const data = await res.json();
    waiting.remove();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");
    history.push({ role: "assistant", content: data.answer, sources: data.sources });
    addBubble("assistant", data.answer, data.sources);
    save();
  } catch (err) {
    waiting.remove();
    addBubble("error", err.message);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", e => { e.preventDefault(); send(); });
input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
document.getElementById("clear").addEventListener("click", () => {
  history = [];
  save();
  chat.querySelectorAll(".msg:not(:first-child)").forEach(el => el.remove());
});
