// Turns the model's simple Markdown (bold, italics, bullets, headings) into safe HTML.
// Everything is escaped first, so no HTML from the model can run on the page.
function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function inlineMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*(?!\s)(.+?)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function formatAnswer(raw) {
  const lines = escapeHtml(String(raw || "")).split(/\r?\n/);
  const out = [];
  let list = null; // "ul" or "ol" while inside a list

  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };

  for (const line of lines) {
    const t = line.trim();
    const bullet = t.match(/^[*\-•]\s+(.*)$/);
    const numbered = t.match(/^\d+[.)]\s+(.*)$/);
    const heading = t.match(/^#{1,4}\s+(.*)$/);
    if (bullet || numbered) {
      const kind = bullet ? "ul" : "ol";
      if (list !== kind) { closeList(); out.push(`<${kind}>`); list = kind; }
      out.push(`<li>${inlineMarkdown((bullet || numbered)[1])}</li>`);
    } else if (heading) {
      closeList();
      out.push(`<h4>${inlineMarkdown(heading[1])}</h4>`);
    } else if (t === "" || /^-{3,}$/.test(t)) {
      closeList();
    } else {
      closeList();
      out.push(`<p>${inlineMarkdown(t)}</p>`);
    }
  }
  closeList();
  return out.join("");
}

function sourcesHtml(sources) {
  if (!sources || !sources.length) return "";
  const seen = new Set();
  const chips = [];
  for (const s of sources) {
    const key = `${s.filename} p.${s.page}`;
    if (seen.has(key)) continue;
    seen.add(key);
    chips.push(`<span class="src-chip">${escapeHtml(s.filename)} · p. ${escapeHtml(String(s.page))}</span>`);
  }
  return `<div class="sources"><span class="src-label">Sources</span>${chips.join("")}</div>`;
}
