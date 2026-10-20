// Small display-only Markdown subset. Raw HTML is always escaped, never executed.
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  })[char]);
}

function inline(text) {
  const tokens = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^\s)]+\))/g;
  let html = '', cursor = 0;
  for (const match of text.matchAll(tokens)) {
    html += escapeHtml(text.slice(cursor, match.index));
    const value = match[0];
    if (value.startsWith('`')) html += `<code>${escapeHtml(value.slice(1, -1))}</code>`;
    else if (value.startsWith('**')) html += `<strong>${escapeHtml(value.slice(2, -2))}</strong>`;
    else if (value.startsWith('*')) html += `<em>${escapeHtml(value.slice(1, -1))}</em>`;
    else {
      const [, label, href] = value.match(/^\[([^\]]+)\]\((.+)\)$/);
      let allowed = false;
      try { allowed = ['http:', 'https:', 'mailto:'].includes(new URL(href, location.href).protocol); }
      catch { /* An invalid link remains plain text. */ }
      html += allowed ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>` : escapeHtml(label);
    }
    cursor = match.index + value.length;
  }
  return html + escapeHtml(text.slice(cursor));
}

const cells = line => line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim());
const tableRule = line => /^\|?[\s:|-]+\|[\s:|-]*$/.test(line) &&
  cells(line).every(cell => /^:?-{3,}:?$/.test(cell));
const listItem = line => line.match(/^\s*(?:([-+*])|(\d+)\.)\s+(.+)$/);
const special = line => /^(#{1,6}\s|>\s?|```|\s*([-+*]|\d+\.)\s|---+$)/.test(line);

export function renderMarkdown(markdown) {
  const lines = String(markdown ?? '').replace(/\r\n?/g, '\n').split('\n');
  const output = [];
  for (let i = 0; i < lines.length;) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    if (line.startsWith('```')) {
      const code = [];
      for (i++; i < lines.length && !lines[i].startsWith('```'); i++) code.push(lines[i]);
      if (i < lines.length) i++;
      output.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`);
    } else if (i + 1 < lines.length && line.includes('|') && tableRule(lines[i + 1])) {
      const headings = cells(line);
      const rows = [];
      for (i += 2; i < lines.length && lines[i].trim() && lines[i].includes('|'); i++) {
        const values = cells(lines[i]);
        rows.push(`<tr>${headings.map((_, index) => `<td>${inline(values[index] || '')}</td>`).join('')}</tr>`);
      }
      output.push(`<div class="sop-table-scroll"><table><thead><tr>${headings.map(cell => `<th scope="col">${inline(cell)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`);
    } else if (/^#{1,6}\s/.test(line)) {
      const [, hashes, title] = line.match(/^(#{1,6})\s+(.*)$/);
      const level = Math.min(6, hashes.length + 1);
      output.push(`<h${level}>${inline(title)}</h${level}>`);
      i++;
    } else if (/^---+$/.test(line.trim())) {
      output.push('<hr>'); i++;
    } else if (/^>\s?/.test(line)) {
      const quote = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) quote.push(lines[i++].replace(/^>\s?/, ''));
      output.push(`<blockquote>${inline(quote.join(' '))}</blockquote>`);
    } else if (listItem(line)) {
      const ordered = Boolean(listItem(line)[2]);
      const tag = ordered ? 'ol' : 'ul';
      const items = [];
      while (i < lines.length) {
        const item = listItem(lines[i]);
        if (!item || Boolean(item[2]) !== ordered) break;
        items.push(`<li>${inline(item[3])}</li>`); i++;
      }
      output.push(`<${tag}>${items.join('')}</${tag}>`);
    } else {
      const paragraph = [line];
      for (i++; i < lines.length && lines[i].trim() && !special(lines[i]); i++) {
        if (i + 1 < lines.length && lines[i].includes('|') && tableRule(lines[i + 1])) break;
        paragraph.push(lines[i]);
      }
      output.push(`<p>${inline(paragraph.join(' '))}</p>`);
    }
  }
  return output.join('\n');
}
