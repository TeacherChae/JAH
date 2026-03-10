# URSUS Visualizer — C# Grasshopper Component 구현 계획

> 작성일: 2026-03-11

---

## 0. 핵심 전제

solver.py가 반환하는 세 가지 데이터:

| 변수 | 타입 | 내용 |
|---|---|---|
| `geometries` | `List<Curve>` | 서울시 **행정동 경계 폴리곤** (닫힌 곡선) |
| `centroids` | `List<Point3d>` | 각 행정동 중심점 |
| `avg_incomes` | `List<double>` | 각 행정동 평균 소득 |

> **중요**: 보간의 기반 geometry는 균일 격자(uniform grid)가 아니라 **실제 행정동 경계 폴리곤**이다.
> 경계를 무시하고 사각 격자만 쓰는 방식은 채택하지 않는다.

---

## 1. 전체 파이프라인

```
solver.py
  geometries (행정동 경계 곡선)
  centroids  (기준점)
  avg_incomes (스칼라 값)
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  C# Script Component                                  │
│                                                       │
│  Step 1. 경계 폴리곤 → Mesh 변환 (삼각분할)            │
│  Step 2. 값 정규화                                     │
│  Step 3. 보간 (IDW / KDE / RBF)                       │
│          — 각 mesh vertex에 대해 계산                  │
│  Step 4. 버텍스 Z 변위 + Color 매핑                    │
│  Step 5. 출력                                         │
└──────────────────────────────────────────────────────┘
        │
        ▼
  mesh         : Mesh  (경계 기반 컬러+높이 곡면)
  flatMesh     : Mesh  (Z=0, 색상만)
  minVal/maxVal: double (범례)
```

---

## 2. Step 1 — 경계 폴리곤 → Mesh 변환

### 방법: Brep 삼각분할

```csharp
// 각 행정동 경계 Curve → 평면 Brep → Mesh
Brep[] planarBreps = Brep.CreatePlanarBreps(boundaryCurve, tolerance);
MeshingParameters mp = MeshingParameters.FastRenderMesh;
mp.MaximumEdgeLength = meshEdgeLen;  // 해상도 제어
Mesh districtMesh = Mesh.CreateFromBrep(planarBreps[0], mp)[0];
```

- `MeshingParameters.MaximumEdgeLength` 으로 버텍스 밀도(보간 해상도) 제어
- 각 행정동마다 독립 Mesh 생성 후 전체 merge도 가능

### 대안: Polyline 직접 삼각분할 (earcut 알고리즘)

- 경계가 이미 `Polyline`으로 주어진 경우
- RhinoCommon에 내장 삼각분할 없으므로 fan triangulation 또는 귀 자르기(ear clipping) 직접 구현
- Brep 경로가 더 안전함

---

## 3. Step 2 — 값 정규화

```csharp
double minV = values.Min();
double maxV = values.Max();
// 0~1 정규화
double t = (v - minV) / (maxV - minV);
```

---

## 4. Step 3 — 보간 기법

쿼리점 = 각 행정동 Mesh의 버텍스 `(vx, vy, 0)`
기준점 = `centroids[i]`와 `values[i]` 쌍

### 4-A. IDW (Inverse Distance Weighting)

```
F(x) = Σ[vᵢ / dᵢᵖ] / Σ[1 / dᵢᵖ]
```

```csharp
static double IDW(Point3d q, List<Point3d> pts, List<double> vals, double power) {
    double num = 0, den = 0;
    for (int i = 0; i < pts.Count; i++) {
        double d = q.DistanceTo(pts[i]);
        if (d < 1e-10) return vals[i];
        double w = 1.0 / Math.Pow(d, power);
        num += w * vals[i];
        den += w;
    }
    return num / den;
}
```

- **파라미터**: `power` p (1~3, 클수록 지역 영향 강조)
- **특성**: 빠름, 구현 단순, 입력점 정확 통과, "bullseye" 아티팩트 있음
- **적합 케이스**: 빠른 프리뷰, 경계 변화 강조

### 4-B. KDE (Gaussian Kernel Density Estimation, value-weighted)

```
F(x) = Σ[vᵢ · exp(-dᵢ²/2h²)] / Σ[exp(-dᵢ²/2h²)]
```

```csharp
static double KDE(Point3d q, List<Point3d> pts, List<double> vals, double bandwidth) {
    double h2 = 2.0 * bandwidth * bandwidth;
    double num = 0, den = 0;
    for (int i = 0; i < pts.Count; i++) {
        double d2 = q.DistanceToSquared(pts[i]);
        double k = Math.Exp(-d2 / h2);
        num += k * vals[i];
        den += k;
    }
    return den < 1e-12 ? 0 : num / den;
}
```

- **파라미터**: `bandwidth` h (UTM 단위, 예: 500m~3000m)
- **특성**: 가장 부드러운 필드, 오버슈트 없음, 입력점 정확 통과 안 함
- **"3D" 효과**: Z 높이를 커널 합으로 직접 쓰면 봉우리 형태 표면 가능
- **적합 케이스**: 넓은 지역 추세 시각화

### 4-C. RBF (Radial Basis Function Interpolation)

```
F(x) = Σ[wᵢ · φ(‖x - xᵢ‖)]
```

φ 옵션:
- **Gaussian**: `exp(-ε²r²)`
- **Thin Plate Spline**: `r² log(r)` — 파라미터 불필요, 가장 자연스러운 곡면

```csharp
// 전처리: n×n 선형시스템 A·w = v 풀기
static double[] SolveRBF(List<Point3d> pts, List<double> vals, double eps) {
    int n = pts.Count;
    double[,] A = new double[n, n];
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) {
            double r = pts[i].DistanceTo(pts[j]);
            A[i, j] = Math.Exp(-eps * eps * r * r);  // Gaussian
        }
    return GaussianElimination(A, vals.ToArray());
}

// 평가
static double EvalRBF(Point3d q, List<Point3d> pts, double[] w, double eps) {
    double f = 0;
    for (int i = 0; i < pts.Count; i++) {
        double r = q.DistanceTo(pts[i]);
        f += w[i] * Math.Exp(-eps * eps * r * r);
    }
    return f;
}
```

- **파라미터**: `epsilon` ε (Gaussian), 또는 TPS는 파라미터 없음
- **특성**: 입력점 정확 통과, 가장 매끄러운 곡면, 점 수 많으면 느림 (O(n³) 전처리)
- **권장**: 행정동 수 ≤ 500 → 실용적
- **적합 케이스**: 최고 품질 시각화

---

## 5. Step 4 — Mesh 버텍스 Z 변위 + Color 매핑

```csharp
// 보간값을 각 vertex에 적용
for (int vi = 0; vi < mesh.Vertices.Count; vi++) {
    Point3f v = mesh.Vertices[vi];
    Point3d q = new Point3d(v.X, v.Y, 0);

    double f = Interpolate(q, centroids, values, method, param);
    double t = (f - minVal) / (maxVal - minVal);  // 0~1

    // Z 변위
    mesh.Vertices[vi] = new Point3f(v.X, v.Y, (float)(f * heightScale));

    // 색상 (두 Color 선형 보간)
    Color c = LerpColor(colorLow, colorHigh, t);
    mesh.VertexColors.SetColor(vi, c);
}

mesh.Normals.ComputeNormals();
mesh.Compact();
```

### 컬러 매핑 옵션

- **2색 lerp**: `colorLow` → `colorHigh`
- **다중 스톱**: ColorBrewer 스타일 (YlOrRd, RdYlBu 등) — 별도 팔레트 배열로 구현

---

## 6. C# 컴포넌트 인터페이스 (Grasshopper)

### 입력

| 이름 | GH 타입 | 설명 |
|---|---|---|
| `geometries` | Curve (List) | 행정동 경계 폴리곤 |
| `centroids` | Point (List) | 행정동 중심점 |
| `values` | Number (List) | 스칼라 값 (avg_incomes) |
| `resolution` | Number | 메시 엣지 최대 길이 (보간 해상도) |
| `method` | Integer | 0=IDW, 1=KDE, 2=RBF |
| `param` | Number | IDW power / KDE bandwidth / RBF epsilon |
| `heightScale` | Number | Z 배율 |
| `colorLow` | Colour | 최솟값 색상 |
| `colorHigh` | Colour | 최댓값 색상 |

### 출력

| 이름 | GH 타입 | 설명 |
|---|---|---|
| `mesh` | Mesh | 컬러+Z 높이 메시 |
| `flatMesh` | Mesh | Z=0 (색상만, 지도 오버레이용) |
| `minVal` | Number | 범례 최솟값 |
| `maxVal` | Number | 범례 최댓값 |

---

## 7. GHX 노드 구성도

```
[File Path]
    │ solver.py 경로
    ▼
[Python 3 Script]
    │ geometries ──────────────────────────────┐
    │ centroids  ─────────────────────────┐    │
    │ avg_incomes ────────────────────┐   │    │
    ▼                                │   │    │
                                     ▼   ▼    ▼
[Number Slider: resolution]  →  [C# Script Component]
[Number Slider: param]       →       │
[Number Slider: heightScale] →       │
[Color Swatch: colorLow]     →       │
[Color Swatch: colorHigh]    →       │
                                     ▼
                               mesh / flatMesh
                               minVal / maxVal
```

---

## 8. 구현 순서

| 단계 | 내용 | 우선순위 |
|---|---|---|
| 1 | 경계 폴리곤 → Brep → Mesh 변환 파이프라인 검증 | 최우선 |
| 2 | IDW 보간 + Mesh Z/Color 적용 (전체 흐름 검증) | 높음 |
| 3 | KDE 보간 추가 | 보통 |
| 4 | RBF (Gaussian Elimination 포함) 추가 | 보통 |
| 5 | 다중 스톱 컬러 팔레트 | 낮음 |
| 6 | .ghx에 C# 컴포넌트 XML 삽입 | 마지막 |

---

## 9. 핵심 RhinoCommon API 참조

| 기능 | API |
|---|---|
| 경계 → Brep | `Brep.CreatePlanarBreps(curve, tol)` |
| Brep → Mesh | `Mesh.CreateFromBrep(brep, meshingParams)` |
| 메시 파라미터 | `MeshingParameters.FastRenderMesh` / `.MaximumEdgeLength` |
| 버텍스 접근 | `mesh.Vertices[i]`, `mesh.Vertices.SetVertex(i, pt)` |
| 버텍스 색상 | `mesh.VertexColors.SetColor(i, color)` |
| 법선 재계산 | `mesh.Normals.ComputeNormals()` |
| 거리 계산 | `Point3d.DistanceTo()`, `Point3d.DistanceToSquared()` |
| 색상 타입 | `System.Drawing.Color` |

---

## 10. 주의사항

- **좌표계**: `geometries`와 `centroids`는 같은 좌표계여야 함 (UTM 또는 미터 단위 권장). GPS(도 단위)면 미터로 변환 필요 → `gps_to_upm.py` 참조
- **RBF 행렬 안정성**: 기준점이 너무 가까우면 ill-conditioned → 정규화(Tikhonov regularization) 추가 고려
- **Mesh 방향**: `Brep.CreatePlanarBreps`가 내부적으로 면 방향을 맞춰주지만, 필요시 `mesh.Flip(true, true, true)` 호출
- **빈 geometries**: null 체크 및 예외처리 필수
