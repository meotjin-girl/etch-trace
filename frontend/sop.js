import {listSops, getSop} from './sop-data.js';
import {escapeHtml, renderMarkdown} from './markdown.js';

export function mountSops() {
  const $ = id => document.getElementById(id);
  let summaries = [], selected = null, request = 0;

  function renderList() {
    const query = $('sopSearch').value.trim().toLocaleLowerCase();
    const filtered = summaries.filter(item =>
      [item.id, item.title, item.category, item.description, ...(item.tags || [])]
        .join(' ').toLocaleLowerCase().includes(query));
    $('sopCount').textContent = `${filtered.length}개 문서 · 샘플`;
    $('sopList').innerHTML = filtered.length ? filtered.map(item =>
      `<button type="button" class="sop-list-item ${item.id === selected ? 'active' : ''}" data-sop-id="${escapeHtml(item.id)}" aria-pressed="${item.id === selected}">
        <span class="sop-document-id">${escapeHtml(item.id)} <span>v${escapeHtml(item.version)}</span></span>
        <strong>${escapeHtml(item.title)}</strong><span class="sop-description">${escapeHtml(item.description)}</span>
        <span class="sop-list-meta">${escapeHtml(item.category)} · ${escapeHtml(item.updatedAt)}</span>
      </button>`).join('') : '<p class="sop-empty">검색 결과가 없습니다. 다른 키워드로 검색해 주세요.</p>';
  }

  async function select(id) {
    const current = ++request;
    selected = id;
    renderList();
    $('sopDetail').innerHTML = '<p class="sop-empty" role="status">문서를 불러오는 중…</p>';
    try {
      const item = await getSop(id);
      if (current !== request) return;
      $('sopDetail').innerHTML = `<header class="sop-document-header">
        <div class="sop-document-id">${escapeHtml(item.id)} <span class="sop-sample-badge">샘플 문서</span></div>
        <h2 tabindex="-1">${escapeHtml(item.title)}</h2>
        <p>${escapeHtml(item.description)}</p>
        <dl class="sop-metadata"><div><dt>버전</dt><dd>${escapeHtml(item.version)}</dd></div><div><dt>최근 개정</dt><dd>${escapeHtml(item.updatedAt)}</dd></div><div><dt>담당</dt><dd>${escapeHtml(item.owner)}</dd></div></dl>
        <div class="sop-tags">${(item.tags || []).map(tag => `<span>${escapeHtml(tag)}</span>`).join('')}</div>
      </header><div class="sop-markdown">${renderMarkdown(item.markdown)}</div>`;
      if (!$('sopPage').hidden && matchMedia('(max-width: 720px)').matches) {
        $('sopDetail').scrollIntoView({block:'start'});
      }
    } catch (error) {
      if (current === request) $('sopDetail').innerHTML = `<p class="sop-empty" role="alert">${escapeHtml(error.message)}</p>`;
    }
  }

  $('sopSearch').addEventListener('input', renderList);
  $('sopList').addEventListener('click', event => {
    const button = event.target.closest('[data-sop-id]');
    if (button) select(button.dataset.sopId);
  });
  listSops().then(items => {
    summaries = items;
    renderList();
    if (items.length) select(items[0].id);
  }).catch(error => {
    $('sopCount').textContent = '문서를 불러오지 못했습니다.';
    $('sopList').innerHTML = `<p class="sop-empty" role="alert">${escapeHtml(error.message)}</p>`;
  });
}
