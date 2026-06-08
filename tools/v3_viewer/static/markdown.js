function renderMarkdown(text) {
  const source = String(text || "");
  if (!source.trim()) return "";
  const chunks = splitFences(source);
  return chunks.map((chunk) => {
    if (chunk.type === "code") {
      return `<pre><code>${escapeHtml(chunk.text)}</code></pre>`;
    }
    return renderMarkdownBlocks(chunk.text);
  }).join("");
}

function renderSmartText(text) {
  const value = String(text || "");
  const trimmed = value.trim();
  if (looksLikeJson(trimmed)) {
    return `<pre>${escapeHtml(prettyJson(trimmed))}</pre>`;
  }
  return `<div class="markdown">${renderMarkdown(value)}</div>`;
}

function splitFences(source) {
  const parts = [];
  const regex = /```[^\n]*\n([\s\S]*?)```/g;
  let cursor = 0;
  let match;
  while ((match = regex.exec(source)) !== null) {
    if (match.index > cursor) {
      parts.push({ type: "text", text: source.slice(cursor, match.index) });
    }
    parts.push({ type: "code", text: match[1] });
    cursor = regex.lastIndex;
  }
  if (cursor < source.length) {
    parts.push({ type: "text", text: source.slice(cursor) });
  }
  return parts;
}

function renderMarkdownBlocks(text) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let paragraph = [];
  let list = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
    paragraph = [];
  };
  const flushList = () => {
    if (!list.length) return;
    blocks.push(`<ul>${list.map((x) => `<li>${inlineMarkdown(x)}</li>`).join("")}</ul>`);
    list = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length + 2;
      blocks.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }
    const bullet = trimmed.match(/^[-*]\s+(.+)$/) || trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      list.push(bullet[1]);
      continue;
    }
    paragraph.push(trimmed);
  }
  flushParagraph();
  flushList();
  return blocks.join("");
}

function inlineMarkdown(text) {
  const links = [];
  const protectedText = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (_, label, url) => {
    links.push({ label, url });
    return `\uE000${links.length - 1}\uE001`;
  });
  let html = escapeHtml(protectedText);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  html = html.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1">$1</a>');
  html = html.replace(/\uE000(\d+)\uE001/g, (_, index) => {
    const link = links[Number(index)];
    if (!link) return "";
    return `<a href="${escapeAttr(link.url)}">${escapeHtml(link.label)}</a>`;
  });
  return html;
}

function looksLikeJson(text) {
  return (text.startsWith("{") && text.endsWith("}")) || (text.startsWith("[") && text.endsWith("]"));
}

function prettyJson(text) {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}
