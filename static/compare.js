// Compare page: asks the same question with and without the papers, side by side.
const cform = document.getElementById("compare-form");
const cq = document.getElementById("cq");
const cbtn = document.getElementById("cbtn");
const withBox = document.getElementById("with");
const withoutBox = document.getElementById("without");

async function askOnce(question, useDocuments) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: [{ role: "user", content: question }], use_documents: useDocuments }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function show(box, promise, withSources) {
  box.innerHTML = '<p class="cp-empty thinking">Writing an answer…</p>';
  return promise.then(data => {
    const note = withSources && !(data.sources || []).length
      ? '<div class="sources"><span class="src-label">No matching passages found</span></div>' : "";
    box.innerHTML = formatAnswer(data.answer) + (withSources ? sourcesHtml(data.sources) : "") + note;
  }).catch(err => {
    box.innerHTML = `<p class="cp-error">${escapeHtml(err.message)}</p>`;
  });
}

async function runCompare() {
  const question = cq.value.trim();
  if (!question || cbtn.disabled) return;
  cbtn.disabled = true;
  withoutBox.innerHTML = '<p class="cp-empty thinking">Waiting for the first answer…</p>';
  // One after the other, so a small laptop is not asked to run two answers at once.
  await show(withBox, askOnce(question, true), true);
  await show(withoutBox, askOnce(question, false), false);
  cbtn.disabled = false;
}

cform.addEventListener("submit", e => { e.preventDefault(); runCompare(); });
cq.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); runCompare(); }
});
document.querySelectorAll(".chip[data-q]").forEach(chip => {
  chip.addEventListener("click", () => { cq.value = chip.dataset.q; runCompare(); });
});
