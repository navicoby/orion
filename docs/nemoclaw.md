-----

## tags: [NemoClaw, OpenClaw, OpenShell, RTX, WSL2, Docker, AI에이전트, 로컬LLM, 보안]
date: 2026-03-17
type: 설정 가이드

# NemoClaw 설치 가이드 (WSL2 Ubuntu 22.04)

> 2026.03.18 설치 완료 기준 | Windows + WSL2 + Docker Desktop 환경

---

## 구조

```
Windows
 └─ WSL2 Ubuntu 22.04 ← OpenShell + NemoClaw 설치
     └─ Docker ← OpenShell이 샌드박스 컨테이너 자동 생성
         └─ Sandbox (ns5) ← OpenClaw 에이전트 실행
```

---

## 사전 요구사항

| 항목 | 요구사양 | 확인 명령어 |
|------|----------|------------|
| WSL | **버전 2 필수** (WSL1 불가) | `wsl -l -v` (PowerShell) |
| Ubuntu | 22.04 LTS 이상 | `lsb_release -a` |
| Docker Desktop | 실행 중 + WSL2 통합 활성화 | `docker ps` |
| Node.js | 22 이상 | `node -v` |
| npm | 10 이상 | `npm -v` |
| NVIDIA API 키 | build.nvidia.com에서 발급 | nvapi-로 시작 |

---

## 설치 순서

### 1단계: Docker Desktop 실행 (Windows)

Docker Desktop 앱 실행 → Settings → Resources → WSL Integration → **Ubuntu-22.04 활성화** 확인

```powershell
# PowerShell에서 확인
docker ps
```

빈 테이블이 나오면 정상.

### 2단계: WSL 진입

```powershell
wsl
```

### 3단계: OpenShell 설치

> ⚠️ **핵심**: OpenShell을 먼저 설치해야 NemoClaw가 작동함. 이 단계를 빠뜨리면 샌드박스 생성 실패.

```bash
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh
openshell --version   # openshell 0.0.10 확인
```

### 4단계: NemoClaw 설치 및 Onboard

```bash
git clone https://github.com/NVIDIA/NemoClaw.git
cd NemoClaw
./install.sh
```

설치 과정에서 자동으로 진행되는 항목 (7단계):

1. **Preflight checks** — Docker, OpenShell CLI, GPU 감지
2. **Gateway 시작** — OpenShell 게이트웨이 생성 (endpoint: https://127.0.0.1:8080)
3. **Sandbox 생성** — 이름 입력 (예: `ns5`), Docker 이미지 빌드 (~5분)
4. **Inference 설정** — **NVIDIA API 키 입력** (nvapi-로 시작하는 키 붙여넣기)
5. **Inference provider** — nvidia-nim 프로바이더 생성, 모델: nemotron-3-super-120b-a12b
6. **OpenClaw 설정** — 샌드박스 내부에 OpenClaw 게이트웨이 실행
7. **Policy 설정** — 기본 프리셋 적용 (pypi, npm) → `Y` 입력

설치 완료 시 출력:

```
──────────────────────────────────────────────────
Sandbox      ns5 (Landlock + seccomp + netns)
Model        nvidia/nemotron-3-super-120b-a12b (NVIDIA Cloud API)
──────────────────────────────────────────────────
```

---

## 사용법

### 샌드박스 접속

```bash
nemoclaw ns5 connect
```

### OpenClaw TUI 실행 (채팅 인터페이스)

```bash
openclaw tui
```

### 상태 확인 / 로그

```bash
nemoclaw ns5 status
nemoclaw ns5 logs --follow
```

---

## 재부팅 후 재접속 (3단계)

1. **Docker Desktop 실행** (Windows 앱 클릭)
2. PowerShell에서 `wsl` 입력
3. WSL 안에서:

```bash
nemoclaw ns5 connect
```

샌드박스가 꺼져있으면:

```bash
nemoclaw ns5 start
nemoclaw ns5 connect
```

---

## 재설치 (초기화)

기존 설치 완전 제거 후 재설치:

```bash
# 정리
sudo npm uninstall -g nemoclaw
rm -rf ~/.nemoclaw ~/NemoClaw /mnt/c/Users/navic/NemoClaw

# OpenShell 재설치
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh

# NemoClaw 재설치
cd ~
git clone https://github.com/NVIDIA/NemoClaw.git
cd NemoClaw
./install.sh
```

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 샌드박스 생성 실패 | OpenShell 미설치 | 3단계부터 다시 |
| `docker ps` 에러 | Docker Desktop 미실행 | Docker Desktop 켜기 |
| `openshell: command not found` | OpenShell 미설치 | `curl -LsSf ...` 재실행 |
| WSL1 사용 중 | Docker 미지원 | `wsl --set-version Ubuntu 2` |
| OOM (메모리 부족) | RAM < 8GB | `.wslconfig`에 `memory=8GB` 설정 |
| API 키 인증 실패 | 키 만료/오타 | build.nvidia.com에서 재발급 |
| `npm warn deprecated` | 의존성 경고 | 무시 (설치에 영향 없음) |
