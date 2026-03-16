-----

## tags: [NemoClaw, OpenClaw, OpenShell, RTX, WSL2, Docker, AI에이전트, 로컬LLM, 보안]
date: 2026-03-17
type: 설정 가이드

# ⚙️ NemoClaw 로컬 설치 가이드 (Windows + WSL2 + NVIDIA GPU)

## NemoClaw란?

- NVIDIA가 GTC 2026에서 발표한 오픈소스 스택 (Apache 2.0)
- OpenClaw + OpenShell(보안 샌드박스) + Nemotron(로컬 LLM) + 프라이버시 라우터
- OpenClaw의 보안 문제(프롬프트 인젝션, 시스템 레벨 접근, 스킬 공급망 리스크)를 해결
- 모든 추론 요청이 샌드박스에서 직접 외부로 나가지 않고 OpenShell 게이트웨이를 경유

## 추론 프로파일

|프로파일       |프로바이더           |모델                     |용도                    |
|-----------|----------------|-----------------------|----------------------|
|`default`  |NVIDIA Cloud API|nemotron-3-super-120b  |프로덕션 (클라우드)           |
|`nim-local`|Local NIM       |nemotron-3-super-120b  |온프레미스 (NVAIE 라이선스 필요) |
|`vllm`     |vLLM            |nemotron-3-nano-30b-a3b|로컬 개발 (무료, RTX GPU 적합)|


> 모든 프로파일에서 OpenShell 보안(샌드박스, 네트워크 정책, 파일시스템 격리)은 동일 적용

## 보안 레이어

|레이어       |보호 대상                    |적용 시점       |
|----------|-------------------------|------------|
|Network   |비인가 아웃바운드 연결 차단          |런타임 핫리로드    |
|Filesystem|/sandbox, /tmp 외 읽기/쓰기 차단|샌드박스 생성 시 잠금|
|Process   |권한 상승, 위험 syscall 차단     |샌드박스 생성 시 잠금|
|Inference |모델 API 호출을 제어된 백엔드로 재라우팅 |런타임 핫리로드    |

## 전제조건

- Windows 11 + WSL2 Ubuntu 22.04+
- Docker Desktop (WSL2 백엔드)
- NVIDIA GPU (RTX 3070 이상 권장, 12GB+ VRAM)
- Windows에 NVIDIA Game Ready 드라이버 설치 (WSL 안에 별도 드라이버 설치 금지)

## 설치 순서

### 1단계: WSL2 준비

```powershell
# PowerShell (관리자)
wsl --install -d Ubuntu
wsl --set-default-version 2
wsl --update
```

systemd 활성화 (K3s/cgroup 필요):

```bash
sudo tee /etc/wsl.conf << 'EOF'
[boot]
systemd=true
[automount]
enabled=true
EOF
```

```powershell
# WSL 재시작
wsl --shutdown
wsl -d Ubuntu-22.04
```

### 2단계: Docker GPU 확인

```bash
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
```

GPU가 표시되면 성공.

### 3단계: OpenShell 설치

```bash
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
openshell --version
```

### 4단계: NemoClaw 설치

```bash
cd ~
git clone https://github.com/NVIDIA/OpenShell.git
git clone https://github.com/NVIDIA/NemoClaw.git
cd ~/NemoClaw
./install.sh
```

온보드 마법사:

1. Sandbox name → 원하는 이름
1. Inference → `1) Local NIM` 또는 `2) Cloud API`
1. Policy presets → `Y` (pypi, npm 기본)

### 5단계: NIM 로컬 인증 (Local NIM 선택 시)

```bash
# NGC Legacy Key로 로그인 (Personal Key가 아닌 Legacy Key 필요)
docker logout nvcr.io
echo "레거시키" | docker login nvcr.io --username '$oauthtoken' --password-stdin
docker pull nvcr.io/nim/nvidia/nemotron-3-nano-30b-a3b:latest
```

> NGC API Key 종류 주의:
> 
> - Personal Key (`nvapi-`로 시작) → NIM pull 불가
> - Legacy Key (`nvapi-` 없음) → NIM pull 가능
> - 발급: https://org.ngc.nvidia.com/setup/api-key 하단 Legacy API Key 섹션

### 5단계 (대안): vLLM 프로파일 (NIM 접근 불가 시)

NIM이 안 될 경우, Cloud API로 설치 완료 후 vLLM 로컬로 전환:

```bash
pip install vllm --break-system-packages

vllm serve nvidia/Nemotron-3-Nano-30B-A3B \
  --host 0.0.0.0 --port 8000 \
  --gpu-memory-utilization 0.9 --max-model-len 32768

# 프로파일 전환 (재시작 불필요)
openshell inference set --provider vllm-local --model nvidia/nemotron-3-nano-30b-a3b
```

> vLLM은 HuggingFace에서 모델을 직접 받으므로 NGC 인증 불필요
> NemoClaw 보안 스택은 동일하게 적용됨

### 6단계: 에이전트 접속

```bash
nemoclaw <이름> connect

# 샌드박스 내부에서:
openclaw tui                                                        # 대화형 TUI
openclaw agent --agent main --local -m "hello" --session-id test    # CLI
```

## 핵심 명령어

|명령어                                                 |설명                       |
|----------------------------------------------------|-------------------------|
|`nemoclaw setup`                                    |풀 셋업 (게이트웨이, 프로바이더, 샌드박스)|
|`nemoclaw <이름> connect`                             |샌드박스 셸 접속                |
|`nemoclaw <이름> status`                              |상태 확인                    |
|`nemoclaw <이름> logs --follow`                       |로그 스트리밍                  |
|`nemoclaw term`                                     |OpenShell TUI (모니터링/승인)  |
|`openshell sandbox list`                            |샌드박스 목록                  |
|`openshell inference set --provider <p> --model <m>`|추론 프로파일 전환               |
|`openshell policy set <이름> --policy <yaml>`         |네트워크 정책 적용               |

## 트러블슈팅

### cgroup 에러 (K3s 네임스페이스 실패)

```
cgroup ["kubepods"] has some missing controllers: cpu, cpuset, hugetlb, memory, pids
```

→ `/etc/wsl.conf`에 `systemd=true` 추가 후 `wsl --shutdown` 재시작

### Docker credential 에러

```
fork/exec /usr/bin/docker-credential-desktop.exe: exec format error
```

→ `echo '{}' > ~/.docker/config.json`

### NIM pull Access Denied

→ Legacy Key 사용 여부 확인. Personal Key(`nvapi-`)로는 불가.
→ 그래도 안 되면 vLLM 프로파일로 전환.

## 참고 링크

- NemoClaw GitHub: https://github.com/NVIDIA/NemoClaw
- OpenShell GitHub: https://github.com/NVIDIA/OpenShell
- NemoClaw 문서: https://docs.nvidia.com/nemoclaw/latest/
- 추론 프로파일: https://docs.nvidia.com/nemoclaw/latest/reference/inference-profiles.html
- 네트워크 정책: https://docs.nvidia.com/nemoclaw/latest/reference/network-policies.html
- vLLM 설정: https://docs.nvidia.com/nemoclaw/latest/inference/set-up-local-vllm.html
