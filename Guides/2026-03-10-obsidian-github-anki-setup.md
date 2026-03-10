---
tags: [setup, guide, obsidian, github, anki, claude-code]
date: 2026-03-10
type: setup-guide
---

# ⚙️ 옵시디언 + GitHub + Anki + Claude Code 연동 가이드

## 배경
맥 환경에서 옵시디언 볼트를 생성하고, GitHub 백업 + Anki 학습 + Claude Code 자동화를 연결하여 '지능형 지식 베이스'를 구축하는 전체 프로세스.

## 준비물
- MacBook (macOS)
- GitHub 계정 + SSH 키 설정 완료
- Homebrew 설치 완료
- Claude Max 구독 ($100/월, Claude Code 포함)

## 완료된 구성

### 볼트 정보
- 볼트명: `orion`
- 경로: `~/Documents/orion` (`/Users/navicoby/Documents/Orion`)
- GitHub: `git@github.com:navicoby/orion.git` (Private)

### 폴더 구조
```
orion/
├── Research/           ← 리서치 리포트 자동 저장
├── Ideas/              ← 아이디어/기획 메모
├── TechNotes/          ← 코딩/기술 노트
├── Guides/             ← 설정 가이드
├── Meetings/           ← 회의/대화 요약
├── CLAUDE.md           ← Claude Code 규칙
├── SKILL.md            ← 리서치 수집 스킬
├── chat-to-vault-SKILL.md ← 대화 정리 스킬
├── .gitignore
└── .claudeignore
```

## 절차

### 1단계: 옵시디언 설치 + 볼트 생성
```bash
brew install --cask obsidian
```
- 앱 실행 → Create new vault → 이름: `orion` → 경로: `~/Documents/`

### 2단계: GitHub 연결
```bash
cd ~/Documents/orion
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin git@github.com:navicoby/orion.git
git push -u origin main
```
- GitHub에서 `orion` 저장소를 Private, 옵션 전부 체크 해제로 생성
- SSH 방식으로 연결 (`git@github.com:` 형식)

### 3단계: Obsidian Git 플러그인
- 설정 → Community plugins → Turn on → Browse → `Obsidian Git` 검색 → Install → Enable
- 5분마다 자동 백업 가능 (Vault backup interval 설정)

### 4단계: .gitignore 설정
```bash
cat > .gitignore << 'EOF'
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/workspaces.json
.DS_Store
EOF
```
- 기기별 충돌 파일 제외, 플러그인/테마 설정은 포함

### 5단계: .claudeignore 설정
```bash
cat > .claudeignore << 'EOF'
.obsidian/
.git/
EOF
```
- Claude Code가 앱 설정과 Git 내부 파일을 건드리지 못하게 보호
- 마크다운 노트는 자유롭게 접근 가능

### 6단계: Claude Code 설치 + 인증
```bash
brew install node          # Node.js 없으면
npm install -g @anthropic-ai/claude-code
claude auth login          # 브라우저에서 로그인
```
- Max 구독 선택, Recommended settings 적용

### 7단계: CLAUDE.md 생성
Claude Code에서:
```
이 폴더는 옵시디언 볼트야. CLAUDE.md 파일을 만들어줘.
```
규칙: 마크다운만 수정, .obsidian 미접촉, 안키 카드는 START/END 형식

### 8단계: Anki 연동
1. Anki 설치 (또는 이미 설치된 경우 그대로 사용)
2. Anki → 도구 → 애드온 → 새로 설치 → 코드: `2055492159` (AnkiConnect)
3. AnkiConnect Config 수정:
```json
{
    "apiKey": null,
    "apiLogPath": null,
    "webBindAddress": "127.0.0.1",
    "webBindPort": 8765,
    "webCorsOrigin": "http://localhost",
    "webCorsOriginList": [
        "http://localhost",
        "app://obsidian.md"
    ]
}
```
4. Anki 재시작
5. 옵시디언 → Obsidian to Anki 플러그인 설치
6. Anki 실행 상태에서 플러그인 토글 끄고 다시 켜기 (중요!)
7. `Cmd + P` → Scan vault

### 안키 카드 올바른 형식 (중요!)
`질문 :: 답변` 형식은 안 됨. 반드시 각 요소가 별도 줄:
```
TARGET DECK: Default

START
Basic
질문 내용?
Back: 답변 내용
END
```

### 9단계: 리서치 자동 수집 예약
```bash
# 스크립트 생성
mkdir -p ~/Documents/orion/scripts
cat > ~/Documents/orion/scripts/auto-research.sh << 'EOF'
#!/bin/bash
cd ~/Documents/orion
claude -p "SKILL.md를 읽고 이번 주 조경BIM, 자연자본 자료를 수집해서 Research 폴더에 마크다운 리포트로 저장하고 git add, commit, push까지 실행해줘. 중간에 질문하지 말고 바로 진행해." --allowedTools "WebSearch,Write,Bash"
EOF
chmod +x ~/Documents/orion/scripts/auto-research.sh

# 매주 월요일 9시 자동 실행
echo "0 9 * * 1 ~/Documents/orion/scripts/auto-research.sh" | crontab -
```

## 트러블슈팅

### remote origin already exists 에러
```bash
git remote remove origin
git remote add origin git@github.com:navicoby/orion.git
git push -u origin main
```

### Anki 카드가 안 보임
- Anki가 실행 중인 상태에서 Obsidian to Anki 플러그인 토글을 끄고 다시 켜기
- 카드 형식이 START/END 블록이고 각 요소가 별도 줄인지 확인
- `TARGET DECK: Default`가 파일 맨 위에 있는지 확인

### Claude Code에서 웹 검색 허락 계속 물어봄
- "Yes, and don't ask again" (2번) 선택

### caffeinate 실행 중
- `Ctrl + C`로 종료 가능, cron 예약과 무관

## 두 번째 맥북 접속 (미완료)
새 맥에서:
```bash
git clone git@github.com:navicoby/orion.git ~/Documents/orion
```
이후 옵시디언에서 해당 폴더 열기 + 동일 환경(Node, Claude Code, Anki) 설치 필요

## 📝 Anki Cards

START
Basic
옵시디언 볼트를 GitHub에 처음 연결하는 명령어 순서는?
Back: git init → git add . → git commit -m "메시지" → git branch -M main → git remote add origin [주소] → git push -u origin main
END

START
Basic
AnkiConnect 애드온 설치 코드는?
Back: 2055492159
END

START
Basic
Obsidian to Anki에서 카드가 인식되려면 어떤 형식이어야 하는가?
Back: START / Basic / 질문 / Back: 답변 / END 각 요소가 반드시 별도 줄에 위치해야 한다
END

START
Basic
Claude Code에서 볼트 작업 시 .claudeignore에 넣어야 할 폴더는?
Back: .obsidian/ 과 .git/ (앱 설정과 Git 내부 파일 보호)
END

START
Basic
맥에서 cron으로 매주 월요일 9시 자동 실행을 예약하는 방법은?
Back: echo "0 9 * * 1 스크립트경로" | crontab - 으로 등록하고, crontab -l 로 확인
END
