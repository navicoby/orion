---
name: chat-to-vault
description: Claude와의 대화 내용을 요약 정리하여 옵시디언 볼트에 마크다운으로 저장하고 GitHub에 자동 push하는 스킬. Use when user says "대화 정리해줘", "이거 볼트에 저장해줘", "요약해서 옵시디언에 올려줘", "메모로 만들어줘", "정리해서 깃허브에 올려줘", "노트로 만들어줘", "아이디어 정리", "기획 정리", "오늘 대화 정리", or any request to summarize, organize, or save conversation content to Obsidian vault. Also trigger when user mentions "md로 만들어줘", "마크다운으로 정리", "볼트에 넣어줘", "깃허브에 push". Do NOT use for research collection (that's landscape-natcap-research skill).
---

# Chat-to-Vault: 대화 정리 → 옵시디언 저장

Claude와 나눈 대화에서 유용한 정보를 추출하여 옵시디언 볼트에 마크다운으로 저장하고 GitHub에 push합니다.

## 볼트 정보
- 경로: `~/Documents/orion`
- GitHub: `git@github.com:navicoby/orion.git`

## 보안 규칙 (필수)

정리 시 아래 민감 정보는 반드시 제외한다:
- API 키, 토큰, 시크릿
- 비밀번호, 인증 정보
- SSH 키, 개인키
- 이메일 주소, 전화번호 등 개인 식별 정보
- 금융 정보 (계좌번호, 카드번호)

민감 정보가 포함된 경우 `[민감정보 제외됨]`으로 대체한다.

## 문서 유형별 템플릿

사용자가 요약을 요청하면, 내용에 맞는 유형을 자동 판단하여 아래 템플릿을 적용한다.

### 유형 1: 아이디어/기획 메모

```markdown
---
tags: [idea, 관련주제태그]
date: YYYY-MM-DD
type: idea
status: draft
---

# 💡 [아이디어 제목]

## 배경
- 왜 이 아이디어가 나왔는지

## 핵심 내용
- 아이디어의 핵심 포인트

## 실행 계획
- [ ] 다음 단계 1
- [ ] 다음 단계 2

## 참고
- 관련 링크나 자료
```

저장 위치: `Ideas/YYYY-MM-DD-제목.md`

### 유형 2: 코딩/기술 노트

```markdown
---
tags: [coding, 언어/프레임워크태그]
date: YYYY-MM-DD
type: tech-note
---

# 🔧 [기술 주제]

## 문제
- 해결하려던 문제

## 해결 방법
- 핵심 코드나 명령어 (코드블록 사용)

## 배운 점
- 핵심 개념 정리

## 📝 Anki Cards

START
Basic
[핵심 개념 질문]
Back: [답변]
END
```

저장 위치: `TechNotes/YYYY-MM-DD-제목.md`

### 유형 3: 설정 가이드

```markdown
---
tags: [setup, guide, 도구태그]
date: YYYY-MM-DD
type: setup-guide
---

# ⚙️ [설정 주제]

## 준비물
- 필요한 도구/계정

## 절차
1. 첫 번째 단계
2. 두 번째 단계
3. ...

## 트러블슈팅
- 자주 발생하는 문제와 해결법

## 📝 Anki Cards

START
Basic
[설정 관련 질문]
Back: [답변]
END
```

저장 위치: `Guides/YYYY-MM-DD-제목.md`

### 유형 4: 회의/대화 요약

```markdown
---
tags: [meeting, summary, 주제태그]
date: YYYY-MM-DD
type: meeting-summary
---

# 📋 [대화 주제]

## 핵심 요약
- 대화의 핵심 내용 3-5줄

## 결정 사항
- 확정된 내용

## 액션 아이템
- [ ] 해야 할 것 1
- [ ] 해야 할 것 2

## 메모
- 추가 참고사항
```

저장 위치: `Meetings/YYYY-MM-DD-제목.md`

## 워크플로우

### Step 1: 내용 분석
사용자가 정리를 요청하면:
1. 대화 내용에서 핵심 정보 추출
2. 문서 유형 자동 판단 (아이디어/코딩/설정/회의)
3. 민감 정보 필터링

### Step 2: 마크다운 생성
1. 해당 유형의 템플릿 적용
2. YAML frontmatter에 적절한 태그 추가
3. 내용이 충분하면 Anki 카드 3-5개 포함
4. 옵시디언 내부 링크(`[[관련노트]]`) 활용 가능하면 추가

### Step 3: 볼트 저장 + GitHub Push
1. 유형별 폴더에 저장 (없으면 자동 생성)
2. 파일명: `YYYY-MM-DD-제목.md`
3. 자동 실행:
```bash
cd ~/Documents/orion
git add .
git commit -m "📝 [유형]: 제목"
git push
```

## 폴더 구조

```
orion/
├── Ideas/          ← 아이디어/기획 메모
├── TechNotes/      ← 코딩/기술 노트
├── Guides/         ← 설정 가이드
├── Meetings/       ← 회의/대화 요약
├── Research/       ← 리서치 리포트 (다른 스킬)
├── CLAUDE.md
├── SKILL.md
└── ...
```

## 사용법

Claude Code에서:
```
cd ~/Documents/orion
claude
```

요청 예시:
- "아까 나눈 옵시디언 세팅 대화 정리해서 볼트에 올려줘"
- "이 아이디어 정리해서 저장해줘: [내용 붙여넣기]"
- "오늘 코딩한 내용 기술노트로 만들어줘"
- "방금 회의 내용 요약해서 볼트에 넣어줘"

## 품질 기준

- 핵심 내용 위주로 간결하게 정리 (불필요한 대화 제거)
- 민감 정보 100% 제외
- YAML frontmatter 필수 포함
- 가능하면 Anki 카드 포함
- 액션 아이템은 체크박스로 표시
- 한국어로 작성 (영문 기술 용어는 그대로 유지)
