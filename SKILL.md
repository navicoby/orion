---
name: landscape-natcap-research
description: 조경 BIM(Landscape BIM)과 자연자본(Natural Capital) 분야의 최신 논문, 기사, 동향을 수집하고 옵시디언 볼트에 마크다운 리포트를 자동 저장한 후 GitHub에 자동 push하는 스킬. Use when user says "자료 수집", "리서치", "논문 찾아줘", "최신 동향", "조경 BIM", "자연자본", "natural capital", "landscape BIM", "생태계 서비스", "ecosystem services", "탄소 크레딧", "biodiversity", "green infrastructure", or any request related to collecting research on landscape architecture, BIM for landscape, natural capital accounting, or ecosystem services. Also trigger when user mentions "GIS AI", "환경영향평가", "탄소중립 조경", "ESG 자연자본", or "NbS (Nature-based Solutions)". Do NOT use for general AI news or unrelated BIM topics like structural/MEP BIM.
---

# Landscape BIM & Natural Capital Research Collector

조경 BIM과 자연자본 분야의 최신 자료를 수집하고, 옵시디언 볼트에 마크다운으로 저장한 후 GitHub에 자동 push합니다.

## 수집 대상 키워드

### 조경 BIM (Landscape BIM)
- Landscape BIM, landscape information modeling
- BIM + landscape architecture, site design, grading
- BIM + GIS integration, terrain modeling
- Digital twin + landscape, park, urban green
- Computational landscape design
- Parametric landscape, algorithmic design

### 자연자본 (Natural Capital)
- Natural capital accounting, natural capital protocol
- Ecosystem services valuation
- Biodiversity net gain (BNG)
- Nature-based Solutions (NbS)
- Carbon credit, carbon sequestration + landscape
- ESG + natural capital, TNFD (Taskforce on Nature-related Financial Disclosures)
- Green infrastructure + valuation
- 환경영향평가 + AI, 생태계 서비스 평가

## 워크플로우

### Step 1: 검색 범위 확인
사용자에게 간단히 확인:
- 기간: 오늘/이번 주/이번 달 (기본: 이번 주)
- 분야: 조경BIM/자연자본 전부 또는 선택
- 소스: 논문/기사/뉴스 전부 또는 선택

사용자가 "자료 수집해줘" 등 간단히 말하면 기본값(이번 주, 전체 분야, 전체 소스)으로 즉시 진행. 추가 질문하지 않는다.

### Step 2: 웹 검색으로 자료 수집

#### 논문
검색 쿼리 예시:
- "landscape BIM digital twin 2026"
- "natural capital accounting 2026"
- "ecosystem services valuation AI"
- "biodiversity net gain assessment"
- "nature-based solutions urban"
- "carbon sequestration landscape design"
- "TNFD nature-related disclosure"
- "parametric landscape architecture"

각 자료에서 수집할 정보:
- 제목
- 저자/출처
- 발행일
- 핵심 요약 (2-3문장, 한국어)
- URL

#### 기사/뉴스
검색 쿼리 예시:
- "landscape BIM news"
- "natural capital news latest"
- "ecosystem services policy"
- "biodiversity credit market"
- "ESG natural capital"

### Step 3: 마크다운 리포트 생성

아래 형식으로 옵시디언 호환 마크다운 파일을 생성한다:

```markdown
---
tags: [research, landscape-bim, natural-capital, weekly-report]
date: YYYY-MM-DD
type: research-report
---

# 📋 조경 BIM & 자연자본 리서치 리포트
> 📅 수집일: YYYY-MM-DD | 📊 범위: [기간]

## 🏗️ 조경 BIM (Landscape BIM)

### 📄 논문 / 학술자료
1. **[제목](URL)**
   - 저자: [저자명] | 출처: [저널/arXiv] | 날짜: [YYYY-MM-DD]
   - 요약: ...

### 📰 기사 / 뉴스
1. **[제목](URL)**
   - 출처: [미디어명] | 날짜: [YYYY-MM-DD]
   - 요약: ...

## 🌿 자연자본 (Natural Capital)

### 📄 논문 / 학술자료
(같은 구조)

### 📰 기사 / 뉴스
(같은 구조)

## 💡 이번 주 핵심 트렌드
- [분야별 주요 흐름 3-5개]

## 📝 Anki Cards

START
Basic
[핵심 개념 질문]
Back: [답변]
END

(주요 개념 3-5개를 안키 카드로 생성)
```

### Step 4: 볼트 저장 + GitHub Push

리포트 생성 후 자동으로:

1. 파일을 옵시디언 볼트의 `Research/` 폴더에 저장
2. 파일명 형식: `YYYY-MM-DD-research-report.md`
3. git add → commit → push 실행

**저장 및 push 스크립트 실행:**
```bash
python3 /path/to/skill/scripts/save_and_push.py --vault-path ~/Documents/orion --file-name "YYYY-MM-DD-research-report.md" --content "마크다운 내용"
```

또는 Claude Code에서 직접:
```bash
# 1. Research 폴더 생성 (없으면)
mkdir -p ~/Documents/orion/Research

# 2. 파일 저장 (Claude Code가 직접 작성)
# Claude Code: "리포트를 ~/Documents/orion/Research/2026-03-08-research-report.md에 저장해줘"

# 3. Git push
cd ~/Documents/orion
git add .
git commit -m "📋 Research report: YYYY-MM-DD"
git push
```

## 볼트 설정

### 볼트 경로
```
~/Documents/orion/
```

### 폴더 구조
```
orion/
├── Research/              ← 리서치 리포트 저장
│   ├── 2026-03-08-research-report.md
│   ├── 2026-03-15-research-report.md
│   └── ...
├── Notes/                 ← 일반 노트
├── CLAUDE.md              ← Claude Code 규칙
├── .gitignore
└── .claudeignore
```

## 품질 기준

- 각 분야별 최소 3개 이상의 자료 수집
- 모든 자료에 URL 포함
- 요약은 한국어로 작성
- 중복 자료 제거
- 날짜순 정렬 (최신 우선)
- 안키 카드 최소 3개 포함
- 옵시디언 태그(YAML frontmatter) 포함

## Claude Code 사용법

Claude Code 터미널에서:
```
cd ~/Documents/orion
claude
```

실행 후 아래와 같이 요청:
- "이번 주 자료 수집해줘"
- "자연자본 최신 논문 찾아줘"
- "조경 BIM 동향 리포트 만들어줘"
- "리서치 리포트 만들고 깃허브에 올려줘"

Claude Code가 자동으로:
1. 웹 검색으로 자료 수집
2. 마크다운 리포트 생성
3. Research/ 폴더에 저장
4. git add → commit → push 실행
