---
layout: default
title: Orion
tags: [BIM, OpenUSD, Qdrant, IFC, 조경설계, Spatial-AI]
date: 2026-03-14
type: TechNotes
---

# BIM-AI 조경 설계 파이프라인 구축 기록

> IFC to OpenUSD 변환, Qdrant 벡터 DB 속성 관리, 조경 수목 분석 대시보드 구축

---

## 1. 프레임워크 설계

### 목표

BIM 기반 조경 설계에서 IFC 속성정보를 OpenUSD 및 벡터 DB로 관리하고, AI 기반 설계 검증과 자연어 질의를 가능하게 하는 통합 파이프라인을 구축한다.

### 5-Layer 아키텍처

| Layer | 역할 | 기술 |
|-------|------|------|
| Layer 1 | 데이터 소스 | IFC 2x3/4.3, IFC 5 (JSON), Point Cloud, Revit |
| Layer 2 | 파싱 및 변환 | IfcOpenShell, IFC-USD Mapper, Property Embedder |
| Layer 3 | 이중 저장소 | OpenUSD Scene Graph + Qdrant Vector DB |
| Layer 4 | AI 엔진 | RAG Retriever + LLM Multi-Agent + Generative Design |
| Layer 5 | 출력 | USD-IFC Export, 3D Viz, Design Review, Digital Twin |

### 핵심 설계 원칙

- 기하 정보(OpenUSD)와 의미 정보(Qdrant)를 분리 저장하되 `ifc_guid`와 `usd_prim_path`로 양방향 연결
- AI 편집 결과는 USD Layer overlay로 저장하여 원본 비파괴
- Qdrant의 멀티벡터(property tensor + spatial vector) 구조로 유사 요소 검색과 근접 검색을 동시 지원

---

## 2. 환경 구성

### 설치

```bash
conda create -n bim-ai python=3.12 -y
conda activate bim-ai
pip install usd-core ifcopenshell qdrant-client streamlit plotly pandas
```

### 설치된 패키지

| 패키지 | 버전 | 역할 |
|--------|------|------|
| usd-core | 26.3 | OpenUSD Python 바인딩 (pxr) |
| ifcopenshell | 0.8.4 | IFC 파싱, geometry 변환 |
| qdrant-client | latest | Qdrant 벡터 DB 클라이언트 |
| streamlit | latest | 웹 대시보드 |
| plotly | latest | 인터랙티브 차트 |
| pandas | latest | 데이터 테이블 처리 |

### Qdrant Docker

```bash
docker run -d -p 6334:6333 --name qdrant_bim qdrant/qdrant
```

기존 qdrant_storage(6333)와 분리하여 6334 포트로 운영.

---

## 3. IFC to OpenUSD 변환

### 파일: ifc_to_usd.py

IFC 파일에서 요소별 geometry를 추출하여 USD Scene Graph로 매핑한다.

처리 흐름:
1. IfcOpenShell로 IFC 파싱 (공간 구조, 요소, PropertySet)
2. `ifcopenshell.geom.create_shape()`으로 geometry를 triangulated mesh로 변환
3. USD Stage 생성: Xform hierarchy (Site - Building - Storey)
4. 요소별 Mesh + `bim:` 네임스페이스 커스텀 속성 (ifcClass, guid, propertySets)
5. .usda 파일 출력

### IFC to USD 매핑 규칙

| IFC 엔티티 | USD 대응 |
|-----------|---------|
| IfcProject | Stage root |
| IfcSite | /BIM/Site Xform |
| IfcBuilding | /BIM/Site/Building Xform |
| IfcBuildingStorey | .../Storey Xform |
| IfcWall, IfcSlab 등 | Mesh + MaterialBinding |
| IfcPropertySet | bim: namespace attribute |
| IfcGlobalId | bim:guid attribute |

### 변환 결과

- 대상 파일: test_ifc.ifc (IFC2X3, 715,772 entities)
- 변환 요소: 691개 (전부 IfcBuildingElementProxy)
- 전체 geometry 변환 성공 (691/691)
- 출력: test_ifc.usda (283.6 MB)

### 인코딩 에러 수정

USDA 미리보기 출력 시 Windows cp949 인코딩 충돌 발생. 수정:

```python
with open(usd_path, "r", encoding="utf-8") as f:
```

---

## 4. IFC to USDZ 변환 (Vision Pro용)

### 파일: ifc_to_usdz.py

USDZ는 Apple AR Quick Look용 패키지 포맷. 기존 변환 로직에 PBR 머티리얼과 USDZ 패키징을 추가.

추가 사항:
- IFC 타입별 UsdPreviewSurface 머티리얼 (벽=흰색, 문=갈색, 유리=반투명 등)
- DoubleSided 활성화 (AR에서 뒷면 렌더링)
- `UsdUtils.CreateNewUsdzPackage()`로 USDZ 패키징

### 머티리얼 바인딩 수정

Vision Pro에서 머티리얼이 적용되지 않는 문제 발생. Apply 호출 필요:

```python
# 수정 전
UsdShade.MaterialBindingAPI(mesh.GetPrim()).Bind(mat)

# 수정 후
binding = UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
binding.Bind(mat)
```

### USDZ 좌표계 이슈

iPad에서 USDZ 열었을 때 흰 화면만 보이는 문제. AR Quick Look은 Y-up, 센티미터 기준:

```python
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 0.01)
```

### USDZ 웹 렌더링 제한

USDZ는 데스크탑 브라우저에서 직접 렌더링 불가. model-viewer(Google)는 데스크탑에서 GLB만 지원한다. 웹 3D 표준은 GLB/glTF이며, USDZ는 Apple 네이티브 앱 전용으로 분리해서 사용해야 한다.

---

## 5. 웹 뷰어

### 파일: viewer.html

파일 업로드 + model-viewer 기반 3D 뷰어. 드래그앤드롭 지원.

실행:
```bash
python -m http.server 8000
# http://localhost:8000/viewer.html
```

GLB 파일은 데스크탑에서 렌더링 가능, USDZ는 iOS/Vision Pro에서만 동작.

### 파일: ifc_to_glb.py

IFC to GLB 변환 스크립트. trimesh 라이브러리를 사용하여 웹 뷰어용 GLB 파일 생성.

---

## 6. IFC 속성 스캔

### 파일: ifc_property_scan.py

PropertySet 구조를 스캔하여 수치/텍스트 속성 목록 추출.

### 스캔 결과

test_ifc.ifc는 속성 정보가 빈약한 상태:
- 전 요소가 IfcBuildingElementProxy로 분류됨
- PropertySet은 Reference 하나뿐
- Revit에서 IFC 내보내기 시 속성 내보내기 옵션이 비활성화 상태였던 것으로 추정

재내보내기 시 확인 사항:
1. Export user defined property sets 체크
2. IFC Class Mapping 테이블에서 패밀리별 IFC 타입 지정
3. IFC4 버전 권장

### 파일: ifc_deep_scan.py

PropertySet이 부족한 경우를 위해 geometry에서 치수(bbox), 위치(centroid), 볼륨을 역추출하는 심층 스캔.

---

## 7. Qdrant 벡터 DB 저장

### 파일: ifc_to_qdrant.py

IFC deep scan 결과를 Qdrant에 멀티벡터 + payload로 저장.

### 벡터 구조

| 벡터 | 차원 | 용도 |
|------|------|------|
| property | 9d | cx, cy, cz, rx, ry, rz, 높이, 볼륨, 정점수 (Euclidean) |
| spatial | 2d | XY 좌표 (근접 검색 특화, Euclidean) |

### Payload 필드

geometry: centroid(cx,cy,cz), bbox 반경(rx,ry,rz), bbox 치수, 볼륨, min/max 좌표
속성: guid, name, reference, storey, psets
연결: usd_prim_path
분류: species_name, species_code, tier, category, planting, spec_H/W/B/R
추가: canopy_area (수평투영면적)

### 간격 분석

나무 간격 검토에서 무게중심 거리가 아닌 표면 간 거리(edge-to-edge)를 사용.
bbox 반경을 차감하여 실제 수관 사이 간격을 계산한다.

```
실제 간격 = centroid 거리 - 반경A - 반경B
```

Voxel 방식은 정밀하지만 메모리 비용 대비 조경 수목 간격 검토에는 과잉.
bbox 반경 방식을 기본으로 채택하고, 정밀 간섭이 필요한 구간만 voxel 검증하는 2단계 접근을 설계.

### 간격 분석 결과

- 분석 대상: 3,455쌍
- 표면간 거리: mean=0.237m, median=0.120m
- 0~0.5m 구간: 2,831쌍 (82%) - 관목 밀식 패턴
- 겹침(overlap): 905쌍 - 대부분 하층 관목과 상층 교목의 수관 겹침 (다층식재 패턴)

### qdrant-client API 변경 대응

최신 qdrant-client에서 `search()` 메서드가 `query_points()`로 변경됨:

```python
# 수정 전
results = client.search(collection_name=COLLECTION, query_vector=("spatial", [x, y]), limit=6)

# 수정 후
results = client.query_points(collection_name=COLLECTION, query=[x, y], using="spatial", limit=6).points
```

---

## 8. 수종 분류

### 파일: species_classify.py

IFC 요소 이름에서 수종명, 규격(H/W/B/R), 식재방식, 카테고리를 파싱하여 Qdrant payload에 직접 업데이트.

### 이름 파싱 패턴

```
L-PL상록교목_스트로브잣나무:H3.0 X W1.5:641072
     ^^^^^^^^ ^^^^^^^^^^^ ^^^^^^^^^^^ ^^^^^^
     category species     specs       ifc_id
```

### 고유 그룹 코드 (species_code)

수종명 + 규격 조합이 고유 그룹을 형성. 같은 수종이라도 규격이 다르면 별도 그룹:

- 스트로브잣나무_H3.0 W1.5 (39주) - 교목
- 스트로브잣나무_H2.5 W1.2 (34주) - 소교목

### 계층 분류 기준

| 계층 | 높이 기준 | 수량 |
|------|----------|------|
| 교목 | H >= 3.0m | 132주 (19%) |
| 소교목 | 1.5 <= H < 3.0m | 87주 (13%) |
| 관목 | 0.8 <= H < 1.5m | 254주 (37%) |
| 지피 | H < 0.8m | 232주 (34%) |

### 분류 결과: 25개 고유 그룹 / 23개 수종

교목 (12그룹):
- 왕벚나무 H4.0 B12 - 26주
- 칠엽수 H3.5 R12 - 19주
- 중국단풍 H3.5 R10 - 5주
- 회화나무 H3.5 R8 - 5주
- 계수나무 H3.0 R12 - 10주
- 청단풍 H3.0 R10 - 13주
- 복자기 H3.0 R10 - 13주
- 산수유 H3.0 W1.5 R10 - 5주
- 스트로브잣나무 H3.0 W1.5 - 39주
- 마가목 H3.0 R8 - 14주
- 산딸나무 H3.0 R8 - 14주
- 층층나무 H3.0 R6 - 7주

소교목 (1그룹):
- 스트로브잣나무 H2.5 W1.2 - 34주

관목 (6그룹):
- 사철나무 H1.2 W0.4 - 108주
- 수수꽃다리 H1.2 W0.4 - 30주
- 황매화 H1.0 W0.4 - 34주
- 흰말채나무 H1.0 W0.4 - 14주
- 화살나무 H0.8 W0.4 - 50주
- 조팝나무 H0.8 W0.4 - 18주

지피 (5그룹):
- 영산홍 H0.3 W0.4 - 46주
- 산철쭉 H0.4 W0.4 - 26주
- 백철쭉 H0.4 W0.4 - 20주
- 자산홍 H0.4 W0.4 - 20주
- 회양목 H0.3 W0.3 - 120주

### 이상치: 미분류 1주

- 이름: "지형 솔리드:경로 - 150mm 목재 판자"
- bbox: 96.5 x 75.3 x 0.9m
- 볼륨: 6,541m3
- 정체: Revit에서 지형(Toposurface)을 바닥 패밀리 타입으로 대체 모델링한 대지면

분석에서 `species_name != ""` 조건으로 자동 제외 처리.

---

## 9. 수관 투영면적 (canopy_area)

bbox_volume(3D 체적)과 별도로 수평투영면적 필요. bbox_dx x bbox_dy로 계산하여 Qdrant payload에 추가:

```python
canopy_area = bbox_dx * bbox_dy  # 단위: m2
```

691개 포인트 일괄 업데이트 완료.

---

## 10. 질의 도구

### 파일: bim_query.py

Qdrant 데이터 대화형 질의 도구.

| 명령 | 기능 |
|------|------|
| stats | 전체 통계 + 볼륨 이상치 |
| species | 수종별 높이/수관폭/볼륨/동종간격 |
| overlap | Z축 분리 겹침 분석 (같은 높이대끼리만 검출) |
| find 키워드 | 특정 수종 상세 + 주변 요소 |
| near x y | XY 좌표 주변 검색 |

---

## 11. Streamlit 대시보드

### 파일: dashboard.py

```bash
streamlit run dashboard.py
```

### 기능

- 사이드바 필터: 계층, 수종, 규격H 범위, 식재방식
- 그룹 기준 전환: species_code / species_name / tier / planting / spec_H / spec_W / spec_R / category / canopy_area
- XY 평면도: 그룹별 색상 분류, 크기=높이, hover 상세
- 그룹 분석: 그룹별 집계표, 선택 시 개체 목록 + 간격 분석
- 차트: 계층별 파이, 수종별 바, 높이 분포, 수관면적 분포, 높이 vs 수관면적 산점도
- 데이터: 필터 적용 원본 테이블 + CSV 다운로드

---

## 12. 생성된 파일 목록

| 파일 | 용도 |
|------|------|
| ifc_to_usd.py | IFC to USDA 변환 |
| ifc_to_usdz.py | IFC to USDZ 변환 (Vision Pro) |
| ifc_to_glb.py | IFC to GLB 변환 (웹 뷰어) |
| viewer.html | 웹 3D 뷰어 (파일 업로드, model-viewer) |
| ifc_property_scan.py | IFC PropertySet 구조 스캔 |
| ifc_deep_scan.py | geometry 역추출 심층 스캔 |
| ifc_to_qdrant.py | IFC deep scan + Qdrant 저장 + 간격분석 |
| species_classify.py | 수종 분류 + Qdrant payload 업데이트 |
| bim_query.py | Qdrant 대화형 질의 도구 |
| dashboard.py | Streamlit 조경 대시보드 |
| BIM-AI-Design-Framework.md | 프레임워크 설계 문서 |

---

## 13. 다음 단계

| 단계 | 상태 | 내용 |
|------|------|------|
| IFC to USD/USDZ 변환 | 완료 | 691개 요소 변환 |
| Qdrant 속성 저장 | 완료 | 멀티벡터 + payload |
| 수종 분류 | 완료 | 25개 고유 그룹 |
| 간격/수종 분석 | 완료 | edge-to-edge, Z축 분리 |
| Streamlit 대시보드 | 완료 | 필터, 평면도, 차트 |
| Revit 속성 재내보내기 | 미완 | 비료량, CO2, 단가 등 누락 속성 확보 |
| 수종 마스터 보강 | 미완 | 외부 CSV로 유지관리/토심 등 매칭 |
| RAG 질의 (LLM 연동) | 미완 | Claude/GPT API 연동 자연어 검색 |
| Multi-Agent 설계 자동화 | 미완 | LangGraph 기반 설계/검토/실행 에이전트 |
| Digital Twin | 미완 | USD + IoT 실시간 연동 |

---

## 14. 참고사항

### IFC 5.0 + OpenUSD 통합 동향

buildingSMART International과 Alliance for OpenUSD(AOUSD)가 공식 협력 협정을 체결. IFC 5는 JSON 직렬화를 채택하여 OpenUSD와의 직접 통합 호환성을 높였다. IFC 5는 bottom-up 데이터 구성 방식으로 AEC 산업의 반복적, 협업적 특성에 적합하며, USD의 top-down 접근과 상호 보완적이다.

### Qdrant 선택 근거

- Rust 기반 고성능
- HNSW 탐색 중 payload filter 직접 적용 (후처리 대비 성능 우위)
- Dense + Sparse 하이브리드 검색
- Binary/Scalar quantization (메모리 최대 64x 절감)
- Multitenancy (프로젝트별 tenant 격리)

### 웹 3D 포맷 현황

- USDZ: Apple 네이티브 앱 전용 (Safari Quick Look, Vision Pro, RealityKit)
- GLB/glTF: 웹 표준 (model-viewer, Three.js, Babylon.js)
- 데스크탑 브라우저에서 USDZ 직접 렌더링하는 웹 라이브러리는 현재 없음
