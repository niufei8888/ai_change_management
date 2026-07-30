// Turning an answer into HTML. Shared by /chat and /console the same way
// answer.css is, and for the same reason: two renderers for one string will
// drift, and a console that displays the product's output differently from the
// product is a poor instrument for judging it.
//
// Hand-written rather than pulling in a markdown library, because there is no
// build step here (TO-22) and the model only ever emits four constructs. It is
// not a markdown implementation and does not try to be -- it covers exactly what
// the synthesize prompt asks for and escapes everything else.

const ANSWER_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };
const escapeHtml = (s) => String(s).replace(/[&<>]/g, (c) => ANSWER_ESCAPES[c]);
const escapeAttr = (s) => escapeHtml(s).replace(/"/g, "&quot;");

// Must agree with SOURCE_LINE in apps/console/src/driftline/checks.py. That
// check blocks a benchmark case on this line's shape, so if the two disagree
// about what counts as one, the console would be linking a citation line the
// checker just failed the case for.
const SOURCE_LINE = /^\s*sources?\s*:/i;

function answerHtml(text, citations = []) {
  const out = [];
  let list = null;
  const closeList = () => {
    if (list) out.push(`</${list}>`);
    list = null;
  };

  for (const line of String(text ?? "").split("\n")) {
    // Requiring whitespace after the marker is what keeps "**bold at the start
    // of a line**" from being read as a bullet.
    const bullet = line.match(/^\s*[*-]\s+(.*\S)\s*$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*\S)\s*$/);
    if (bullet || numbered) {
      const kind = bullet ? "ul" : "ol";
      if (list !== kind) {
        closeList();
        out.push(`<${kind}>`);
        list = kind;
      }
      out.push(`<li>${inlineHtml((bullet || numbered)[1])}</li>`);
      continue;
    }

    closeList();
    const trimmed = line.trim();
    if (!trimmed) continue;

    const heading = trimmed.match(/^(#{2,3})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      out.push(`<h${level}>${inlineHtml(heading[2])}</h${level}>`);
      continue;
    }
    out.push(`<p>${SOURCE_LINE.test(trimmed) ? sourceHtml(trimmed, citations) : inlineHtml(trimmed)}</p>`);
  }

  closeList();
  return out.join("");
}

function inlineHtml(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

// The model writes "Source: <title>, <title>" as plain prose and has to keep
// doing so: runner._cited() finds the citations by looking for those titles in
// the answer, and _cites_real_article() blocks on the line's exact shape. So the
// links are added here at render time, from the titles the backend already
// resolved to URLs. Longest first, so "Object Consistency" cannot claim part of
// "Character and Object Consistency" -- the same ordering, for the same reason,
// as the citation check itself.
function sourceHtml(line, citations) {
  const spans = [];
  for (const cite of [...citations].sort((a, b) => b.title.length - a.title.length)) {
    // A scheme check rather than trust: everything downstream of an href is the
    // browser's to interpret, and `javascript:` is a valid URL. These come from
    // our own build-time corpus, so this should never fire -- but an unlinked
    // title is a much better failure than a clickable one that runs code.
    if (!/^https?:\/\//i.test(cite.url || "")) continue;
    // Every occurrence, not just the first: the first one may sit inside a
    // longer title that has already been claimed, while a later standalone
    // mention is still the shorter article's own.
    for (let from = 0; ; ) {
      const start = line.indexOf(cite.title, from);
      if (start < 0) break;
      const end = start + cite.title.length;
      if (!spans.some(([s, e]) => start < e && end > s)) spans.push([start, end, cite.url]);
      from = end;
    }
  }
  spans.sort((a, b) => a[0] - b[0]);

  let html = "";
  let cursor = 0;
  for (const [start, end, url] of spans) {
    const title = escapeHtml(line.slice(start, end));
    html += inlineHtml(line.slice(cursor, start));
    html += `<a href="${escapeAttr(url)}" target="_blank" rel="noopener">${title}</a>`;
    cursor = end;
  }
  return html + inlineHtml(line.slice(cursor));
}
