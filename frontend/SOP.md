# SOP 화면 데이터 연동

SOP 화면은 API 8·9번(`docs/development/frontend.md` 필요 API)을 호출합니다. 실제 backend에는 아직
없으므로 `npm run dev:mock`의 목업(`frontend/mock/fixtures.ts` 샘플)으로 확인합니다.
샘플은 실제 작업 지침이 아니라고 목록과 본문에 표시합니다.

## 교체할 경계

`src/api/client.ts`의 `sops()`·`sop(id)`가 인증 헤더를 붙여 호출합니다.

- `GET /api/sops`: 문서 요약 배열 반환. 본문 마크다운은 포함하지 않습니다.
- `GET /api/sops/{id}`: 요약 정보와 `markdown` 원문 반환. 없으면 404.

목록과 상세에서 사용하는 필드:

```js
{
  id: 'SOP-ETCH-12',
  title: '식각 공정 이상 대응 절차',
  category: '공정 이상 대응',
  version: '1.2',
  updatedAt: '2026-10-12', // YYYY-MM-DD
  owner: '공정기술팀',
  description: '목록에 표시할 문서 소개',
  tags: ['식각', 'Endpoint'],
  demo: true,
  markdown: '## 목적\n본문...' // 상세 조회에서만 필요
}
```

`src/views/SopView.vue`가 검색·선택·상세 로딩을 담당합니다. 연속 선택 시 이전 요청의 응답이
최신 선택을 덮어쓰지 않습니다. 현재 검색은 내려받은 요약 정보에 적용되며,
향후 문서 수가 늘어나면 검색어와 페이지를 서버에 전달하도록 확장합니다.
인증과 최종 문서 권한 검사는 실제 API 연동 시 백엔드에서 적용해야 합니다.
서버 데이터로 교체할 때는 고정된 샘플 안내와 배지도 실제 `demo` 값에 맞게 바꿉니다.

## 마크다운 표시

`src/lib/markdown.ts`의 `renderMarkdown`은 제목·문단·단순 목록·인용·코드 블록·표·강조·링크를 지원하는
소규모 표시 전용 렌더러입니다. 완전한 CommonMark 구현은 아닙니다.
원시 HTML은 이스케이프하며 이미지·실행 스크립트·중첩 목록·고급 확장은 지원하지 않습니다.
링크 프로토콜은 HTTP·HTTPS·메일로 제한합니다.
실제 SOP의 마크다운 규격을 확정한 뒤 확장이 필요하면 전용 파서와 HTML 정화 정책을
검토하고, 문서 원문은 렌더링된 HTML과 분리해 유지합니다.
