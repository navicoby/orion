# LAS → 3D Gaussian Splatting 워크플로우 가이드

**작성일:** 2026-03-09
**환경:** Windows, RTX 4080 (12GB VRAM), 32GB RAM, CUDA 12.9
**데이터:** LAS 포인트클라우드 (6GB, 2억 포인트) + 현장 사진 127장

---

## 1. 프로젝트 개요

LiDAR로 스캔한 6GB LAS 포인트클라우드와 현장 사진 127장을 활용하여 3D 모델을 생성하고, Apple Vision Pro에서 시각화하는 것이 목표다. 두 가지 경로를 동시에 진행했다.

- **경로 A:** LAS → Poisson Surface Reconstruction → OBJ/PLY 메쉬
- **경로 B:** 사진 127장 → COLMAP → Gaussian Splatting → PLY 스플랫

---

## 2. 경로 A: LAS → 메쉬 변환 (Poisson Reconstruction)

### 2.1 환경 설정

```bash
conda create -n las2mesh python=3.11 -y
conda activate las2mesh
pip install laspy[lazrs] open3d numpy trimesh
```

> **주의:** Open3D는 Python 3.12까지만 지원 (2026년 3월 기준). 3.13 이상에서는 설치 불가.

### 2.2 LAS 파일 정보 확인

```python
import laspy

las = laspy.read("pointcloud.las")
print(f"Point count: {las.header.point_count:,}")
print(f"Point format: {las.header.point_format.id}")
print(f"Fields: {list(las.point_format.dimension_names)}")
print(f"Min bounds: {las.header.mins}")
print(f"Max bounds: {las.header.maxs}")
```

**결과:**
- 포인트 수: 200,000,000 (2억)
- 포맷: 3 (RGB 포함)
- 필드: X, Y, Z, intensity, return_number, classification, red, green, blue 등
- 영역: 약 1,300m × 960m, 높이 -15m ~ 133m (UTM 좌표계)

### 2.3 변환 스크립트 (`convert.py`)

```python
import laspy
import open3d as o3d
import numpy as np

# ===== Step 1: Chunked Read =====
print("Step 1: Reading LAS file...")
all_points = []
all_colors = []
with laspy.open("pointcloud.las") as f:
    for chunk in f.chunk_iterator(5_000_000):
        xyz = np.vstack([chunk.x, chunk.y, chunk.z]).T
        rgb = np.vstack([chunk.red, chunk.green, chunk.blue]).T.astype(np.float64)
        if rgb.max() > 255:
            rgb = rgb / 65535.0
        else:
            rgb = rgb / 255.0
        all_points.append(xyz)
        all_colors.append(rgb)
        print(f"  loaded {sum(len(p) for p in all_points):,} points...")
points = np.concatenate(all_points)
colors = np.concatenate(all_colors)
del all_points, all_colors
print(f"Total: {len(points):,} points\n")

# ===== Step 2: Create PointCloud =====
print("Step 2: Creating point cloud...")
pcd = o3d.geometry.PointCloud()
pcd.points = o3d.utility.Vector3dVector(points)
pcd.colors = o3d.utility.Vector3dVector(colors)
del points, colors

# ===== Step 3: Voxel Downsample =====
print("Step 3: Downsampling (voxel=0.05m)...")
pcd = pcd.voxel_down_sample(voxel_size=0.05)
print(f"After downsample: {len(pcd.points):,} points\n")

# ===== Step 4: Outlier Removal =====
print("Step 4: Removing outliers...")
pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
print(f"After cleanup: {len(pcd.points):,} points\n")

# ===== Step 5: Normal Estimation =====
print("Step 5: Estimating normals...")
pcd.estimate_normals(
    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.10, max_nn=30)
)
pcd.orient_normals_towards_camera_location(
    camera_location=np.array([199000, 541500, 200])
)
print("Normals done\n")

# ===== Step 6: Poisson Reconstruction =====
print("Step 6: Poisson reconstruction (depth=10)...")
mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
    pcd, depth=10
)
print(f"Mesh: {len(mesh.vertices):,} vertices, {len(mesh.triangles):,} triangles\n")

# ===== Step 7: Trim by Density =====
print("Step 7: Trimming low-density faces...")
densities = np.asarray(densities)
threshold = np.quantile(densities, 0.01)
mesh.remove_vertices_by_mask(densities < threshold)
mesh.remove_degenerate_triangles()
mesh.remove_duplicated_triangles()
mesh.remove_duplicated_vertices()
mesh.remove_non_manifold_edges()
print(f"After trim: {len(mesh.vertices):,} vertices, {len(mesh.triangles):,} triangles\n")

# ===== Step 8: Center to Origin =====
print("Step 8: Centering to origin...")
verts = np.asarray(mesh.vertices).copy()
verts -= verts.mean(axis=0)
mesh.vertices = o3d.utility.Vector3dVector(verts)
print("Centered\n")

# ===== Step 9: Export =====
print("Step 9: Exporting...")
o3d.io.write_triangle_mesh("output_model.ply", mesh, write_vertex_colors=True)
o3d.io.write_triangle_mesh("output_model.obj", mesh, write_vertex_colors=True)
print("Done! Files: output_model.ply, output_model.obj")
```

### 2.4 파라미터 가이드

| 파라미터 | 값 | 설명 |
|---|---|---|
| voxel_size | 0.05m | 5cm 간격 다운샘플. 2억→수백만 포인트로 축소 |
| voxel_size | 0.10m | 10cm. 빠르지만 거칠다. 테스트용 |
| depth | 8 | 거친 메쉬, 빠름 |
| depth | 9 | 일반적 권장 |
| depth | 10 | 정밀, 느리고 RAM 많이 사용. 32GB에서 가능 |
| depth | 11+ | 32GB에서 OOM 위험 |
| quantile | 0.01 | 밀도 하위 1% 제거. 넓은 표면 유지 |

### 2.5 메모리 관리 주의사항

- 2억 포인트 × (좌표+색상) = 약 10GB 원본. Open3D 변환 시 20GB 이상 사용
- 32GB 시스템에서 OS + 백그라운드 = 10GB 이상 점유. 실제 여유 20GB 정도
- Step 6 (Poisson)에서 추가 5~8GB 사용
- **불필요한 프로그램(브라우저 등) 닫고 실행 권장**
- 터져도 파일 손상 없음. 파라미터 조절 후 재실행

### 2.6 좌표계 이슈

원본 LAS가 UTM 좌표 (198,000 ~ 542,000 범위)라 원점에서 수백km 떨어져 있다. Blender/Rhino에서 보이지 않는 문제 발생.

**해결:** 센터링 스크립트

```python
verts = np.asarray(mesh.vertices).copy()
verts -= verts.mean(axis=0)
mesh.vertices = o3d.utility.Vector3dVector(verts)
```

### 2.7 결과

- 첫 시도 (voxel 0.10, depth 9): 203,743 정점, 412,550 삼각형, 34MB OBJ
- 메쉬가 듬성듬성 → voxel 0.05, depth 10으로 재실행하여 품질 개선

### 2.8 Blender에서 OBJ 버텍스 컬러 보기

Blender OBJ 임포터는 버텍스 컬러를 바로 표시하지 않는다.

1. 오브젝트 선택 → Material Properties
2. New → Base Color 옆 노란 점 → Color Attribute 선택
3. 뷰포트를 Material Preview 모드로 변경

또는 PLY 포맷으로 열면 버텍스 컬러가 바로 나온다.

---

## 3. 경로 B: 사진 → Gaussian Splatting

### 3.1 버전 호환 매트릭스 (핵심!)

네 가지가 반드시 맞아야 한다:

| 구성요소 | 최종 확정 버전 | 역할 |
|---|---|---|
| Python | 3.10 (cp310) | 언어 런타임. 휠 호환 |
| PyTorch | 2.4.0 (pt24) | 딥러닝 프레임워크 |
| CUDA | 12.4 (cu124) | GPU 연산 런타임 |
| gsplat | 1.4.0 | Gaussian 래스터라이저 |
| nerfstudio | 1.1.5 | 학습 프레임워크 |
| COLMAP | 3.13.0 | SfM (카메라 포즈 추출) |

> **교훈:** 시스템 CUDA (nvcc 12.9)와 PyTorch CUDA 런타임 (cu121/cu124)이 맞지 않으면 gsplat DLL 로드 실패. **프리빌드 휠** 사용이 핵심 해결책.

### 3.2 환경 설정 (검증된 순서)

```bash
# 1. 가상환경 생성 (Python 3.10 필수)
conda create -n gsplat python=3.10 -y
conda activate gsplat

# 2. PyTorch + CUDA 12.4
pip install torch==2.4.0 torchvision --index-url https://download.pytorch.org/whl/cu124

# 3. gsplat 프리빌드 휠 (컴파일 건너뜀 → 버전 충돌 원천 차단)
pip install gsplat==1.4.0 --extra-index-url https://docs.gsplat.studio/whl/pt24cu124

# 4. gsplat 의존성 (자동 설치 안 될 경우)
pip install ninja jaxtyping typeguard

# 5. nerfstudio
pip install nerfstudio

# 6. ffmpeg (nerfstudio 이미지 전처리용)
conda install ffmpeg -y
```

### 3.3 COLMAP 설치 (별도)

- https://github.com/colmap/colmap/releases 에서 CUDA 빌드 다운로드
- 압축 해제 후 `bin` 폴더를 시스템 PATH에 추가
- 환경 변수 편집: 시스템 변수 > Path > 새로 만들기 > `D:\COLMAP\bin`
- **PowerShell 새로 열어야** PATH 반영됨

> **주의:** COLMAP 3.13은 nerfstudio의 `ns-process-data`와 호환 안 됨 (`--SiftExtraction.use_gpu` 옵션 제거됨). 수동으로 COLMAP을 실행해야 한다.

### 3.4 COLMAP 수동 실행

```bash
# 폴더 생성
mkdir D:\Spatial_AI\GS\processed\sparse\0

# 1. 특징점 추출 (CUDA 자동 사용)
colmap feature_extractor --database_path D:\Spatial_AI\GS\processed\database.db --image_path D:\Spatial_AI\GS\images --ImageReader.single_camera 1 --ImageReader.camera_model OPENCV

# 2. 매칭 (120장 = 7,140쌍 비교, 10~30분)
colmap exhaustive_matcher --database_path D:\Spatial_AI\GS\processed\database.db

# 3. 매핑 (카메라 위치 + 3D 포인트 생성)
colmap mapper --database_path D:\Spatial_AI\GS\processed\database.db --image_path D:\Spatial_AI\GS\images --output_path D:\Spatial_AI\GS\processed\sparse\0
```

> **참고:** COLMAP 3.13은 결과를 `sparse\0\0`에 저장할 수 있다. nerfstudio 경로 지정 시 확인 필요.

### 3.5 Splatfacto 학습

```bash
ns-train splatfacto colmap \
  --data D:\Spatial_AI\GS\processed \
  --colmap-path sparse\0\0 \
  --images-path ..\images \
  --downscale-factor 1
```

| 옵션 | 설명 |
|---|---|
| `--downscale-factor 1` | 원본 해상도 (디테일 최대, VRAM 부담) |
| `--downscale-factor 2` | 절반 해상도 (VRAM 절약) |
| `--downscale-factor 4` | 1/4 해상도 (빠르지만 품질 손실) |

- 기본 30,000 스텝. RTX 4080 원본 해상도 기준 12~16시간 소요
- 웹 뷰어: `http://localhost:7007`에서 실시간 확인 가능
- GPU 3D 엔진 99% 사용 = 정상 (CUDA 코어 풀가동)

### 3.6 품질 향상 옵션

```bash
ns-train splatfacto colmap \
  --data D:\Spatial_AI\GS\processed \
  --colmap-path sparse\0\0 \
  --images-path ..\images \
  --downscale-factor 1 \
  --max-num-iterations 50000 \
  --pipeline.model.stop-split-at 25000
```

- `--max-num-iterations 50000`: 정제 시간 늘림
- `--pipeline.model.stop-split-at 25000`: Gaussian 분할을 더 오래 유지

### 3.7 출력 및 뷰어

학습 완료 후 PLY 스플랫 파일이 `outputs/` 폴더에 생성된다.

**Apple Vision Pro에서 보기:**
- GaussianViewer, Splat Player, SCONE 등 visionOS 앱에서 PLY 스플랫 직접 로드
- 메쉬 변환 불필요

**USDZ로 변환이 필요한 경우 (메쉬 기반):**
- 스플랫 → 메쉬 추출 (SuGaR/TSDF) → Blender에서 텍스처 베이킹 → USDZ 익스포트

---

## 4. 트러블슈팅 로그

### 4.1 Open3D 설치 실패
- **증상:** `No matching distribution found for open3d`
- **원인:** Python 3.13에서 Open3D 미지원
- **해결:** Python 3.11 이하로 환경 재생성

### 4.2 gsplat DLL 로드 실패
- **증상:** `ImportError: DLL load failed while importing gsplat_cuda`
- **원인:** 시스템 nvcc(12.9)와 PyTorch CUDA(12.1/12.4) 버전 불일치
- **해결:** 프리빌드 휠 사용 `--extra-index-url https://docs.gsplat.studio/whl/pt24cu124`

### 4.3 gsplat 프리빌드 휠 없음
- **증상:** `No matching distribution found for gsplat`
- **원인:** Python 3.11용(cp311) 휠이 존재하지 않음. cp310만 제공
- **해결:** Python 3.10으로 환경 재생성

### 4.4 COLMAP ns-process-data 호환 실패
- **증상:** `unrecognised option '--SiftExtraction.use_gpu'`
- **원인:** COLMAP 3.13에서 해당 옵션 제거
- **해결:** COLMAP 수동 실행 (3.4절 참조)

### 4.5 Blender/Rhino에서 모델 안 보임
- **증상:** 임포트 후 빈 화면
- **원인:** UTM 좌표계 (원점에서 수백km 떨어진 좌표)
- **해결:** 센터링 스크립트로 원점 이동 (2.6절 참조)

### 4.6 PowerShell 경로 공백 문제
- **증상:** `Unrecognized options: AI\GS\images`
- **해결:** 따옴표로 감싸기 `"D:\Spatial AI\GS\images"` 또는 폴더명에서 공백 제거

---

## 5. 대안 오픈소스 Gaussian Splatting 도구

### 5.1 fVDB Reality Capture (NVIDIA)

- **GitHub:** https://github.com/openvdb/fvdb-core
- **특징:** NVIDIA 직접 개발. NanoVDB 기반 GPU 가속, 대규모(1억 Gaussian) 처리 가능
- **장점:** 멀티 GPU 지원, 메쉬 추출 내장, 최고 수준 최적화
- **라이선스:** Apache 2.0 (무료, 상업 사용 가능)
- **비고:** 비교적 새로움. 설치/설정이 nerfstudio보다 복잡할 수 있음

### 5.2 Inria 3DGS (원본)

- **GitHub:** https://github.com/graphdeco-inria/gaussian-splatting
- **특징:** 논문 저자 공식 코드. Gaussian Splatting의 원조
- **장점:** 레퍼런스 구현, 학술적 검증
- **단점:** Ubuntu 기반 설치 권장, Windows에서 까다로움

### 5.3 gsplat (nerfstudio)

- **GitHub:** https://github.com/nerfstudio-project/gsplat
- **특징:** nerfstudio 팀의 Gaussian 래스터라이저 재구현
- **장점:** 사용자 친화적, 활발한 커뮤니티, 웹 뷰어 내장
- **단점:** 프리빌드 휠이 cp310만 지원 (2026년 3월 기준)

### 5.4 3DGRut (NVIDIA)

- **GitHub:** https://github.com/nv-tlabs/3dgrut
- **특징:** NVIDIA Research. 3D Gaussian 기반 실시간 렌더링 툴킷
- **장점:** 고품질 렌더링, NVIDIA GPU 최적화

### 5.5 NuRec

- **특징:** Neural Reconstruction 도구
- **장점:** 메쉬 추출에 강점

### 5.6 기타 도구

| 도구 | 특징 |
|---|---|
| PostShot | 유료, GUI 기반, 쉬움 |
| Luma AI | 클라우드 기반, 앱으로 촬영→자동 변환 |
| Polycam | iPhone 앱, LiDAR + 클라우드 처리 |
| SuGaR | 스플랫→메쉬 추출 특화 |
| 2DGS | 2D Gaussian 기반, 표면 품질 우수 |

### 5.7 COLMAP 대안

| 도구 | 특징 |
|---|---|
| GLOMAP | Google 개발, COLMAP보다 빠름 |
| hloc | COLMAP보다 정확, 더 복잡 |
| OpenMVG | 오픈소스 SfM 대안 |
| TrackGS | COLMAP-Free. 글로벌 피처 트랙으로 포즈 추정 (연구 단계) |

---

## 6. Vision Pro 출력 포맷 정리

| 포맷 | 방법 | 색상 | 비고 |
|---|---|---|---|
| USDZ (메쉬) | Blender에서 텍스처 베이킹 후 익스포트 | O (텍스처 필요) | visionOS 네이티브 |
| PLY (스플랫) | Splatfacto 학습 결과 직접 사용 | O (내장) | GaussianViewer 앱 필요 |
| OBJ (메쉬) | Open3D/Poisson 출력 | O (버텍스 컬러) | 범용 뷰어 |

---

## 7. 하드웨어 요구사항 정리

| 항목 | 최소 | 권장 | 최적 |
|---|---|---|---|
| GPU VRAM | 8GB | 12GB (4080) | 24GB (4090) |
| RAM | 16GB | 32GB | 64GB+ |
| CUDA | 12.1 | 12.4 | 12.4 |
| 저장공간 | 50GB | 100GB | SSD 권장 |

> **M시리즈 Mac 참고:** 256GB 통합메모리(예: M5 Ultra)면 다운샘플 없이 원본 처리 가능. depth 12도 가능. 단, CUDA 없음 (이 파이프라인은 CPU 기반이라 무관).

---

## 8. 전체 워크플로우 요약

```
[LAS 포인트클라우드 6GB]
    │
    ├── 경로 A: 메쉬 생성 (CPU)
    │   laspy → Open3D → Poisson → OBJ/PLY
    │   └── Blender → 텍스처 베이킹 → USDZ → Vision Pro
    │
    └── 경로 B: Gaussian Splatting (GPU/CUDA)
        사진 127장 → COLMAP → Splatfacto → PLY 스플랫
        └── GaussianViewer 앱 → Vision Pro

[대안 도구]
    fVDB Reality Capture, 3DGRut, NuRec, Inria 3DGS
```

---

## 9. 향후 과제

- fVDB Reality Capture로 같은 사진 127장 처리하여 품질/속도 비교
- LAS 포인트클라우드를 Splatfacto 초기화에 활용하는 방법 실험
- Vision Pro에서 스플랫 vs 메쉬 시각적 품질 비교
- 멀티 GPU 환경에서 대규모 처리 테스트
