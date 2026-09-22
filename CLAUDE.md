# Orion Vault

이 볼트는 개인 지식 베이스(Obsidian vault)입니다.

## 규칙

- 마크다운 파일(.md)만 수정할 것
- `.obsidian` 폴더는 절대 건드리지 말 것
- 안키(Anki) 카드는 START/END 블록 형식을 사용할 것
  - 파일 맨 위에 `TARGET DECK: Default` 추가
  - 각 카드는 `START` / `Basic` / `질문` / `Back: 답변` / `END` 블록으로 작성
- 자료 수집, 리서치, 논문 찾기 요청 시 `SKILL.md`를 먼저 읽고 그 형식에 따라 리포트를 생성할 것
  - 리포트는 `Research/` 폴더에 저장
  - 저장은 로컬에서 끝내며 자동 커밋·전송하지 않는다.
  - 사용자가 업로드를 명시한 경우에만 내용을 검토한 보고서 한 개를 `scripts/save_and_push.py --report Research/파일명.md --vault-path . --publish`로 검사·전송한다.
  - 개인 노트·대화·회의록과 `.obsidian` 설정은 업로드 대상에 넣지 않는다.
