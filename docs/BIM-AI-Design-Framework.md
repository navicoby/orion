---
layout: default
title: BIM-AI 설계 프레임워크
---

# BIM-AI 설계 프레임워크

> IFC → OpenUSD 변환, Qdrant 벡터 DB 기반 속성 관리, LLM 멀티에이전트 설계 자동화

---

## 프레임워크 개요

```
[IFC / Point Cloud / Revit]
        ↓
[Layer 2] IfcOpenShell → IFC-USD Mapper → Property Embedder
        ↓                                      ↓
[Layer 3] OpenUSD Scene Graph  ←→  Qdrant Vector DB
        ↓                                      ↓
[Layer 4] RAG Retriever + LLM Multi-Agent + Generative Design
        ↓
[Layer 5] USD→IFC Export / 3D Viz / Design Review / Digital Twin
        ↓
      Feedback Loop → Layer 2 재순환
```

---

## Layer 1 — 데이터 소스

| 포맷 | 용도 | 비고 |
|------|------|------|
| IFC 2x3 / 4.3 | 레거시 BIM 모델 | ISO 16739, 업계 표준 |
| IFC 5 (JSON) | 차세대 표준 | JSON 직렬화, OpenUSD 통합 설계 |
| Point Cloud | 현장 스캔 (LAS/E57) | SLAM 기반 현실 데이터 |
| Revit / Archicad | BIM 저작 도구 | API 통한 직접 연동 |
| CityGML / GIS | 도시·인프라 스케일 | BIM-GIS 통합 |

---

## Layer 2 — 파싱 & 변환

### 2-1. IfcOpenShell 파서

IFC 파일에서 요소, 속성, 관계, 지오메트리를 추출하는 핵심 라이브러리.

```python
import ifcopenshell
import ifcopenshell.util.element as util

model = ifcopenshell.open("model.ifc")

for wall in model.by_type("IfcWall"):
    psets = util.get_psets(wall)          # 속성 세트 전체
    location = util.get_container(wall)   # 공간 위치 (층)
    wall_type = util.get_type(wall)       # 타입 정보
```

- 지원: IFC2x3 TC1, IFC4 Add2 TC1, IFC4x3 Add2
- 지오메트리 → triangulated mesh 변환 (`ifcopenshell.geom`)
- IfcConvert CLI로 glTF, OBJ, DAE 등 일괄 변환 가능

### 2-2. IFC → OpenUSD 매핑 전략

| IFC 엔티티 | USD 대응 | 설명 |
|-----------|---------|------|
| `IfcProject` | Stage root | USD 파일 루트 |
| `IfcSite` | `/Site` Xform | 좌표계 기준점 |
| `IfcBuilding` | `/Site/Building` Xform | 건물 단위 |
| `IfcBuildingStorey` | `.../Storey_1F` Xform | 층 단위 |
| `IfcWall`, `IfcSlab` 등 | Mesh + MaterialBinding | 요소별 지오메트리 |
| `IfcPropertySet` | Custom attribute (`bim:` namespace) | 속성 보존 |
| `IfcRelation` | USD Relationship | 공간·타입·재료 관계 |
| `IfcGlobalId` | `bim:guid` attribute | 양방향 추적 키 |

**핵심 원칙**: 무손실 라운드트립. IFC→USD→IFC 왕복 시 속성 및 관계 정보가 보존되어야 함.

### 2-3. Property Embedder

BIM 요소의 속성을 벡터로 변환하여 의미 검색을 가능하게 하는 모듈.

```python
def serialize_element(element, psets: dict) -> str:
    """BIM 요소를 구조화된 텍스트로 직렬화"""
    lines = [
        f"Type: {element.is_a()}",
        f"Name: {element.Name}",
        f"Storey: {get_storey(element)}",
    ]
    for pset_name, props in psets.items():
        for key, val in props.items():
            lines.append(f"{pset_name}.{key}: {val}")
    return "\n".join(lines)

# 임베딩 생성
text = serialize_element(wall, psets)
vector = embedding_model.encode(text)  # 1536d dense vector
```

**임베딩 모델 선택지**:
- `text-embedding-3-large` (OpenAI) — 범용, 1536d
- 도메인 fine-tuned Sentence-BERT — AEC 용어 특화 시 정확도 향상
- Multilingual 모델 — 한국어 속성명 처리 필수

---

## Layer 3 — 이중 저장소

### 3-1. OpenUSD Scene Graph

**역할**: 기하 정보 + 공간 계층 + 시각화

- **Composition arcs**: Reference, Sublayer, Variant로 다중 소스 합성
- **Layer overlay**: AI 편집 결과를 별도 레이어로 저장 → 원본 비파괴
- **Custom schema**: `bim:ifcClass`, `bim:guid`, `bim:psetHash` 등으로 IFC 메타데이터 보존
- **Variant set**: 설계 대안을 USD Variant로 관리 → 즉시 전환 가능

```
model.usda          ← 원본 IFC 변환 결과
├── ai_edits.usda   ← AI 생성 설계 변경 (sublayer)
├── review.usda     ← 검토 코멘트 레이어
└── iot_live.usda   ← 실시간 센서 데이터 레이어
```

### 3-2. Qdrant Vector DB

**역할**: 속성 기반 의미 검색 + 하이브리드 필터링

```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue
)

client = QdrantClient(host="localhost", port=6333)

# 컬렉션 생성
client.create_collection(
    collection_name="bim_elements",
    vectors_config={
        "dense": VectorParams(size=1536, distance=Distance.COSINE),
        "sparse": VectorParams(size=30000, distance=Distance.DOT),  # BM25
    }
)

# BIM 요소 삽입
client.upsert(
    collection_name="bim_elements",
    points=[PointStruct(
        id=element_id,
        vector={
            "dense": dense_embedding,
            "sparse": sparse_embedding,
        },
        payload={
            "ifc_guid": wall.GlobalId,
            "ifc_class": "IfcWall",
            "storey": "2F",
            "material": "concrete_200mm",
            "usd_prim_path": "/Site/Building/Storey_2F/Wall_001",
            "pset_summary": "Pset_WallCommon.IsExternal: True, ...",
        }
    )]
)

# 하이브리드 검색: 의미 + 필터
results = client.search(
    collection_name="bim_elements",
    query_vector=("dense", query_embedding),
    query_filter=Filter(must=[
        FieldCondition(key="storey", match=MatchValue(value="2F")),
        FieldCondition(key="ifc_class", match=MatchValue(value="IfcWall")),
    ]),
    limit=10,
)
```

**Qdrant 선택 이유**:
- **Payload filter**: HNSW 탐색 중 적용 → 후처리 필터 대비 성능 우위
- **Hybrid search**: Dense(의미) + Sparse(키워드) 동시 쿼리
- **Quantization**: Binary/Scalar quantization으로 메모리 최대 64x 절감
- **Rust 기반**: 고부하에서도 안정적 성능
- **Multitenancy**: 프로젝트별 tenant 격리 가능

### 3-3. 양방향 링크 구조

```
┌─────────────────┐         ┌─────────────────┐
│  OpenUSD Prim    │         │  Qdrant Point    │
│                  │         │                  │
│  bim:guid ───────┼────→────┼─ payload.guid    │
│  prim_path ◄─────┼────←────┼─ payload.usd_path│
│                  │         │                  │
│  geometry (mesh) │         │  vector (1536d)  │
│  hierarchy       │         │  payload (filter)│
└─────────────────┘         └─────────────────┘
```

의미 검색 결과에서 `usd_prim_path`로 즉시 3D 뷰 점프.
3D 뷰에서 선택한 요소의 `bim:guid`로 Qdrant 유사 요소 검색.

---

## Layer 4 — AI 엔진

### 4-1. RAG 파이프라인

```
사용자 질의 (자연어)
    ↓
Query Embedding (dense + sparse)
    ↓
Qdrant Hybrid Search (+ payload filter)
    ↓
Top-K BIM 요소 + PropertySet 컨텍스트
    ↓
USD Scene에서 geometry/hierarchy 보강
    ↓
LLM (Claude / GPT-4) → 답변 생성
```

**질의 예시**:
- "2층 외벽 중 단열 성능이 가장 낮은 벽체는?"
- "이 건물에서 내화 1시간 미만인 구조 부재를 찾아줘"
- "지하 주차장 기둥 간격이 설계 기준에 맞는지 확인해"

### 4-2. LLM Multi-Agent System

LangGraph 또는 AutoGen 기반 4-에이전트 구조:

| Agent | 역할 | 도구 접근 |
|-------|------|----------|
| `design_agent` | 설계 의도 해석, 파라메트릭 조건 생성 | Qdrant search, USD read |
| `checker_agent` | 건축법규/구조기준 적합성 검토 | 법규 DB, IFC validation |
| `coordinator_agent` | 에이전트 간 조율, 충돌 해소 | 전체 에이전트 통신 |
| `executor_agent` | 검증된 코드를 BIM 도구에서 실행 | Revit API, Dynamo, USD write |

**워크플로우**: 사용자 프롬프트 → design_agent가 설계안 생성 → checker_agent가 검증 → 통과 시 executor_agent가 USD Layer에 기록 → 실패 시 design_agent에 피드백.

### 4-3. Generative Design

- 입력: 설계 제약 (법규, 구조, 에너지, 동선)
- 처리: 파라메트릭 알고리즘 + LLM 기반 최적화
- 출력: 다수의 설계 대안 → USD Variant Set으로 저장
- 평가: 자동 스코어링 (에너지 성능, 법규 적합도, 비용)

---

## Layer 5 — 출력 & 피드백

| 출력 채널 | 기술 | 용도 |
|----------|------|------|
| USD → IFC 역변환 | IfcOpenShell write API | 기존 BIM 워크플로우 복귀 |
| 3D 시각화 | Omniverse / Three.js USD Viewer | 웹·VR 기반 리뷰 |
| 자동 설계 검토 | Rule-based + LLM checker | 코드 체크, 충돌 감지 |
| Digital Twin | USD + IoT 스트리밍 | 실시간 운영 모니터링 |

**피드백 루프**: AI 편집 결과 → Property Embedder 재실행 → Qdrant 벡터 갱신 → 다음 검색에 최신 상태 반영.

---

## 기술 스택 요약

| 영역 | 기술 | 버전/비고 |
|------|------|----------|
| IFC 파싱 | IfcOpenShell | 0.8.x, Python/C++ |
| Scene graph | OpenUSD (pxr) | Pixar USD, Python 바인딩 |
| Vector DB | Qdrant | 1.17+, Rust, Gridstore 엔진 |
| Embedding | text-embedding-3-large | 1536d, 또는 도메인 fine-tuned |
| LLM | Claude / GPT-4 | RAG + Agent 활용 |
| Agent framework | LangGraph 또는 AutoGen | Multi-agent orchestration |
| Visualization | Omniverse / Three.js | USD 네이티브 렌더링 |
| CI/CD | IFC 변경 감지 → 자동 파이프라인 | Git-ops 연동 |

---

## 구현 우선순위 (제안)

```
Phase 1: IFC → USD 변환 파이프라인 (IfcOpenShell + pxr)
Phase 2: Qdrant 속성 저장 + 하이브리드 검색 구축
Phase 3: RAG 기반 BIM 질의응답 시스템
Phase 4: Multi-Agent 설계 자동화
Phase 5: Generative Design + Digital Twin 통합
```

---

*2025.03 기준 최신 동향 반영. IFC 5.0 + OpenUSD 통합은 buildingSMART-AOUSD 공식 협력으로 진행 중.*
