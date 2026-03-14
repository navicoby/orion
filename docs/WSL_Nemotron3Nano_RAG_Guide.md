# WSL Nemotron 3 Nano - Local RAG 구축 가이드

## 1. 개요

Nemotron 3 Nano 30B 모델을 Windows 로컬 환경에서 구동하고, Qdrant 벡터 DB와 연계하여 논문 기반 RAG(Retrieval-Augmented Generation) 질의 시스템을 구축하는 과정을 정리한다.

### 시스템 사양

| 항목 | 사양 |
|------|------|
| GPU | NVIDIA RTX **** Laptop (12GB VRAM) |
| RAM | 32GB |
| OS | Windows + WSL (Ubuntu) |
| 저장소 | D:\***** |

### 구성 요소

| 요소 | 역할 | 위치 |
|------|------|------|
| Ollama | LLM 서빙 (Nemotron 3 Nano 30B) | Windows 로컬 |
| Qdrant | 벡터 DB (논문 저장) | Docker (port 6333) |
| bge-m3 | 임베딩 모델 (1024차원, 다국어) | Ollama |
| pdf_rag.py | PDF -> Qdrant 저장 | C:\Users\***\ |
| rag_query.py | 질문 -> 검색 -> 답변 | ~/rag_query.py (WSL) |

---

## 2. Nemotron 3 Nano 모델 선정

Nemotron 3 패밀리는 NVIDIA에서 개발한 오픈 모델군이다.

| 모델 | 총 파라미터 | 활성 파라미터 | 최소 메모리 (Q4) |
|------|------------|-------------|-----------------|
| Nano | 30B | 3.6B | ~24GB |
| Super | 120B | 12B | ~64GB |
| Ultra | 253B | - | 미공개 |

4080 Laptop(12GB VRAM) + 32GB RAM 환경에서는 Nano Q4 양자화 버전이 적정이다. MoE(Mixture of Experts) 구조로 활성 파라미터가 3.6B에 불과하여 추론 효율이 높다.

Super 모델은 Q4 기준 최소 64GB 이상 필요하여 현재 사양으로는 구동 불가하다.

---

## 3. Ollama 설치 및 모델 다운로드

### 3.1 Ollama 설치

ollama.com에서 Windows 설치파일을 다운로드하여 설치한다. 별도 Docker, Python 설정 불필요.

### 3.2 모델 다운로드

```powershell
ollama pull nemotron-3-nano
ollama pull bge-m3
```

nemotron-3-nano는 약 24GB, bge-m3는 약 1.2GB이다.

### 3.3 DNS 오류 대응

Cloudflare R2 저장소 DNS 해석 실패 시 (`no such host` 에러):

```powershell
ipconfig /flushdns
```

지속 시 DNS 서버 변경:

```powershell
netsh interface ip set dns "Wi-Fi" static 8.8.8.8
netsh interface ip add dns "Wi-Fi" 1.1.1.1 index=2
```

### 3.4 설치 확인

```powershell
ollama list
```

nemotron-3-nano, bge-m3가 목록에 있으면 정상이다.

---

## 4. Qdrant 벡터 DB 확인

기존에 Docker로 구축된 Qdrant가 있다. 볼륨 데이터는 `/var/lib/docker/volumes/qdrant_storage/_data`에 저장되어 있다.

### 4.1 컨테이너 확인 및 시작

```powershell
docker ps -a | findstr qdrant
docker start qdrant
```

### 4.2 컬렉션 확인

```powershell
curl http://localhost:6333/collections
```

### 4.3 대시보드

브라우저에서 `http://localhost:6333/dashboard` 접속.

### 4.4 현재 데이터 현황

| 항목 | 값 |
|------|-----|
| 컬렉션명 | my_documents |
| 총 벡터 수 | 4727개 |
| 벡터 차원 | 1024 |
| 유사도 | Cosine |
| 임베딩 모델 | bge-m3 (Ollama 경유) |

---

## 5. PDF 저장 스크립트 (pdf_rag.py)

PDF 파일을 500자 단위로 청크하여 bge-m3로 임베딩 후 Qdrant에 저장한다. 이미 저장된 파일은 건너뛰고 새 파일만 처리한다.

### 5.1 설정

- PDF 폴더: `C:\Users\***\Documents\pdf_doc`
- 컬렉션: `my_documents`
- 배치 크기: 50

### 5.2 실행 (WSL)

```bash
python3 /mnt/c/Users/***/pdf_rag.py
```

WSL에서 실행 시 PDF 폴더 경로는 `/mnt/c/Users/***/Documents/pdf_doc`으로 변환하여 사용한다.

### 5.3 Ollama 접속 설정

WSL에서 Windows의 Ollama에 접근할 때 `localhost`가 아닌 `$(hostname).local:11434`를 사용해야 한다.

```python
embeddings = OllamaEmbeddings(model="bge-m3", base_url="http://***.local:11434")
```

### 5.4 중복 처리

`get_existing_sources()` 함수가 Qdrant에서 이미 저장된 파일명을 조회하여 새 PDF만 처리한다. 기존 데이터의 마지막 ID 이후부터 새 벡터를 저장한다.

### 5.5 배치 스킵

PDF에서 추출된 텍스트 중 특수문자, 수식, 깨진 문자가 포함된 청크는 임베딩 시 NaN 값이 발생하여 해당 배치가 스킵될 수 있다. 소량이므로 무시해도 무방하다.

---

## 6. RAG 질의 스크립트 (rag_query.py)

질문을 입력하면 Qdrant에서 관련 문서를 검색하고, Nemotron 3 Nano가 해당 문서를 참고하여 답변을 생성한다.

### 6.1 동작 흐름

```
질문 입력
  -> bge-m3가 질문을 벡터로 변환
  -> Qdrant에서 유사 문서 Top 5 검색
  -> 검색된 문서 + 질문을 Nemotron 3 Nano에 전달
  -> 스트리밍 답변 생성
```

### 6.2 실행 (WSL)

```bash
python3 ~/rag_query.py
```

### 6.3 WSL 네트워크 설정

WSL에서 Windows의 Ollama와 Docker의 Qdrant에 각각 접근해야 한다.

| 서비스 | WSL에서의 접속 주소 |
|--------|-------------------|
| Ollama | http://***.local:11434 |
| Qdrant | http://localhost:6333 |

hostname은 환경에 따라 다를 수 있으며, `socket.gethostname()`으로 자동 감지한다.

### 6.4 Qdrant 클라이언트 호환성

qdrant_client 최신 버전에서는 `search()` 대신 `query_points()`를 사용한다. 반환값은 `QueryResponse` 객체이며, `list(results.points)`로 변환하여 사용한다.

### 6.5 프롬프트 구조

```
You are a helpful research assistant.
Answer the question based on the provided context.
If the context doesn't contain enough information, say so honestly.
Answer in the same language as the question.

Context: [검색된 문서 5개]
Question: [사용자 질문]
```

---

## 7. WSL 환경 설정

### 7.1 필요 패키지

```bash
pip install qdrant-client langchain-ollama requests pymupdf
```

### 7.2 Ollama 연결 테스트

```bash
curl http://$(hostname).local:11434/api/version
```

### 7.3 Qdrant 연결 테스트

```bash
curl http://localhost:6333/collections
```

---

## 8. 파일 구조

```
C:\Users\***\
  pdf_rag.py                 -- PDF 저장 스크립트
  rag_query.py               -- (백업용)
  Documents\pdf_doc\         -- PDF 원본 폴더
    articles.pdf
    Exploring the performance of protected areas...pdf
    (+ 20여 편의 논문)

~/  (WSL Home)
  rag_query.py               -- 질의 스크립트 (실행용)

Docker
  qdrant                     -- 벡터 DB 컨테이너
    Volume: /var/lib/docker/volumes/qdrant_storage/_data
```

---

## 9. RAG vs 파인튜닝

| 구분 | RAG (현재 구현) | 파인튜닝 |
|------|----------------|---------|
| 방식 | 질문 시 DB에서 문서 검색 후 참고 | 모델 자체에 지식 내재화 |
| 비유 | 오픈북 시험 | 클로즈드북 시험 |
| 장점 | 즉시 적용, 데이터 추가 용이 | 별도 검색 불필요, 빠른 응답 |
| 단점 | 매번 검색 필요 | 학습 비용, 망각 문제 |
| 현재 환경 적합성 | 적합 (로컬에서 바로 가능) | 4080 12GB로는 30B 학습 불가 |

현재 환경에서는 RAG가 최적이며, 논문을 지속적으로 추가하여 DB를 확장하는 방식으로 운영한다.

---

## 10. 운영 절차 요약

### 논문 추가

1. PDF를 `C:\Users\***\Documents\pdf_doc` 폴더에 복사
2. WSL에서 `python3 /mnt/c/Users/***/pdf_rag.py` 실행
3. 새 PDF만 자동 처리되어 Qdrant에 저장

### 질문

1. `docker start qdrant` (Qdrant 미실행 시)
2. WSL에서 `python3 ~/rag_query.py` 실행
3. 질문 입력 -> 답변 확인
4. `quit` 입력 시 종료

### 상태 확인

```bash
# 모델 목록
ollama list

# Qdrant 컬렉션 정보
curl http://localhost:6333/collections/my_documents

# Qdrant 대시보드
# 브라우저: http://localhost:6333/dashboard
```
