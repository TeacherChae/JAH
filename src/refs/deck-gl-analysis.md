# deck.gl 레포 분석

> 분석 날짜: 2026-03-11
> 대상: `/home/keonchae/deck.gl` (v9.3.0-alpha.1)
> 출처: github.com/visgl/deck.gl

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 버전 | 9.3.0-alpha.1 |
| 라이선스 | MIT |
| 패키지 매니저 | Yarn 1.22.19 (Workspaces) + Lerna |
| Node 요구사항 | >=20 |
| 빌드 도구 | Ocular (@vis.gl/dev-tools) + TypeScript |
| 패키지 구조 | Yarn Workspaces 모노레포 (18 모듈) |

WebGL2 기반 **GPU 가속 지리 시각화 렌더링 엔진**. kepler.gl의 핵심 렌더링 레이어로 사용되며, 수백만 개의 데이터 포인트를 브라우저에서 실시간으로 렌더링한다.

---

## 2. 전체 아키텍처

```
User Data + Layer Config
  │
  ▼
Deck Instance
  ├── LayerManager   ─── 레이어 라이프사이클 조율
  ├── ViewManager    ─── 뷰포트/카메라 관리
  ├── EffectManager  ─── 조명·포스트프로세싱 이펙트
  └── DeckPicker     ─── 피킹(클릭/호버) 처리
          │
          ▼
  Layer Instance (e.g., ScatterplotLayer)
    ├── updateState()  ─── props 변경 감지 → attribute 갱신 요청
    └── AttributeManager
          │  CPU에서 계산한 속성 값 → GPU 버퍼에 업로드
          ▼
  GPU Resources (luma.gl)
    ├── Buffer (position, color, size ...)
    ├── Model (shader + geometry)
    └── Texture
          │
          ▼
  Rendering Passes
    ├── LayersPass     ─── 실제 화면 렌더링
    ├── PickLayersPass ─── FBO에 고유 색상으로 렌더 (피킹용)
    └── ShadowPass     ─── 그림자 매핑
          │
          ▼
  WebGL2 Framebuffer → Screen
```

### 렌더링 패스 상세

1. **LayersPass**: 레이어별 순서로 `layer.draw()` 호출 → 화면에 출력
2. **PickLayersPass**: 동일 레이어를 오프스크린 FBO에 고유 색상으로 렌더 → 픽셀 읽기로 오브젝트 특정
3. **ShadowPass**: 조명 효과 시 그림자 맵 생성

---

## 3. 모듈 구조 (18 모듈)

### 핵심 렌더링
| 모듈 | 역할 |
|---|---|
| `@deck.gl/core` | 베이스 렌더링 엔진 (Layer, Deck, Viewport, Controller) |
| `@deck.gl/layers` | 13개 표준 레이어 타입 |
| `@deck.gl/geo-layers` | 18개 지리 공간 레이어 타입 |
| `@deck.gl/aggregation-layers` | 5개 데이터 집계 레이어 |
| `@deck.gl/mesh-layers` | 3D 메시 렌더링 |
| `@deck.gl/extensions` | 8개 플러그인 확장 |
| `@deck.gl/main` | 전체 패키지 통합 export |

### 통합
| 모듈 | 역할 |
|---|---|
| `@deck.gl/react` | React 컴포넌트 래퍼 (`<DeckGL>`) |
| `@deck.gl/json` | JSON 기반 레이어 설정 렌더링 |
| `@deck.gl/mapbox` | Mapbox 베이스맵 통합 |
| `@deck.gl/google-maps` | Google Maps 통합 |
| `@deck.gl/arcgis` | ArcGIS JavaScript API 통합 |
| `@deck.gl/carto` | CARTO 서비스 레이어 |
| `@deck.gl/widgets` | UI 컴포넌트 (나침반, 줌 등) |
| `@deck.gl/test-utils` | 레이어 개발용 테스트 유틸 |
| `@deck.gl/jupyter-widget` | Jupyter 노트북 위젯 |

### 바인딩
| 바인딩 | 역할 |
|---|---|
| `pydeck` | Python 래퍼 (JSON config 생성) |
| `pydeck-carto` | Python CARTO 전용 |

---

## 4. 레이어 타입 전체 목록

### @deck.gl/layers (13개 — 기본 레이어)

| 레이어 | 용도 |
|---|---|
| `ScatterplotLayer` | 산점도, 점 밀도 시각화 |
| `LineLayer` | 선분 연결 |
| `PathLayer` | 연속 경로 |
| `PolygonLayer` | 채워진 다각형 |
| `SolidPolygonLayer` | 단색 다각형 (대안 구현) |
| `ColumnLayer` | 3D 압출 기둥 |
| `GridCellLayer` | 그리드 셀 (ColumnLayer 변형) |
| `IconLayer` | 스프라이트 아이콘/마커 |
| `TextLayer` | 텍스트 레이블 |
| `BitmapLayer` | 비트맵 오버레이 |
| `ArcLayer` | 곡선 호 (두 지점 연결) |
| `GeoJsonLayer` | GeoJSON 피처 렌더링 (복합) |
| `PointCloudLayer` | LAS/LAZ 포인트 클라우드 |

### @deck.gl/aggregation-layers (5개 — 집계)

| 레이어 | 용도 |
|---|---|
| `HexagonLayer` | 육각형 빈 집계 |
| `GridLayer` | 정사각 격자 집계 |
| `ScreenGridLayer` | 스크린 공간 격자 |
| `HeatmapLayer` | 커널 밀도 추정 |
| `ContourLayer` | 등고선 |

### @deck.gl/geo-layers (18개+ — 지리 공간)

**타일 기반**
| 레이어 | 용도 |
|---|---|
| `TileLayer` | 범용 XYZ 타일 |
| `MVTLayer` | Mapbox Vector Tiles |
| `WMSLayer` | OGC Web Map Service |
| `Tile3DLayer` | Cesium 3D Tiles |
| `TerrainLayer` | 지형/고도 타일 |

**공간 인덱스**
| 레이어 | 용도 |
|---|---|
| `H3HexagonLayer` | Uber H3 육각 셀 |
| `H3ClusterLayer` | H3 클러스터링 |
| `S2Layer` | Google S2 셀 |
| `QuadkeyLayer` | Quadkey 타일링 |
| `A5Layer` | A5 공간 인덱스 |
| `GeohashLayer` | Geohash 그리드 |

**기타**
| 레이어 | 용도 |
|---|---|
| `TripsLayer` | 이동 궤적 애니메이션 |
| `GreatCircleLayer` | 대권 호 |

### @deck.gl/mesh-layers (2개)

| 레이어 | 용도 |
|---|---|
| `SimpleMeshLayer` | 단일 glTF 모델 per item |
| `ScenegraphLayer` | 계층형 씬 그래프 |

---

## 5. 핵심 파일 구조 (core/src/)

```
modules/core/src/
├── lib/
│   ├── layer.ts                 # 베이스 Layer 클래스 (46KB)
│   ├── composite-layer.ts       # 서브레이어를 포함하는 부모 레이어
│   ├── layer-manager.ts         # 전역 레이어 라이프사이클 관리
│   ├── deck.ts                  # 메인 Deck 인스턴스 (46KB)
│   ├── deck-picker.ts           # 피킹 시스템
│   ├── layer-extension.ts       # 확장 인터페이스
│   └── attribute/               # GPU 속성 버퍼 관리
├── viewports/
│   ├── viewport.ts
│   ├── web-mercator-viewport.ts
│   ├── orthographic-viewport.ts
│   └── orbit-viewport.ts
├── views/                       # 뷰 클래스 (컨트롤러와 쌍)
│   ├── map-view.ts
│   ├── first-person-view.ts
│   └── orbit-view.ts
├── controllers/                 # 입력 처리 (마우스/터치/키보드)
├── shaderlib/                   # 셰이더 모듈
│   ├── project/                 # 좌표 투영 (GLSL + WGSL 양쪽)
│   ├── color/
│   ├── picking/
│   └── shadow/
├── passes/                      # 렌더 패스
│   ├── layers-pass.ts
│   ├── pick-layers-pass.ts
│   └── shadow-pass.ts
└── effects/
    └── lighting/
        ├── ambient-light.ts
        ├── directional-light.ts
        └── point-light.ts
```

---

## 6. 좌표계 시스템 (5종)

| 이름 | 값 | 입력 형식 | 단위 |
|---|---|---|---|
| `LNGLAT` | 1 | [경도, 위도, 고도] | 도, 미터 |
| `CARTESIAN` | 0 | [x, y, z] | 임의 |
| `METER_OFFSETS` | 2 | [dx, dy, dz] from origin | 미터 |
| `LNGLAT_OFFSETS` | 3 | [dlon, dlat, elev] from origin | 도, 미터 |
| `DEFAULT` | -1 | 뷰 타입에 따라 자동 감지 | - |

좌표 변환은 `project` 셰이더 모듈에서 GPU 상에서 수행. `@math.gl/web-mercator` 사용.

---

## 7. 피킹(Picking) 시스템

```
마우스 이벤트 (mjolnir.js)
  ↓
DeckPicker.pickByPoint()
  ↓
PickLayersPass — 오프스크린 FBO에 고유 RGB 색상으로 렌더
  ↓
커서 위치 픽셀 읽기 → RGB 디코드 → (레이어 ID + 오브젝트 인덱스)
  ↓
layer.getPickingInfo() — 좌표 역투영 + 메타데이터 추가
  ↓
onHover / onClick 콜백 호출
```

**PickingInfo 구조**:
```typescript
{
  layer: Layer;
  object: any;          // 원본 데이터 아이템
  index: number;        // 데이터 배열 인덱스
  x, y: number;         // 스크린 좌표
  coordinate?: [lon, lat, z]; // 월드 좌표
}
```

---

## 8. 확장(Extensions) 시스템 (8개)

| 확장 | 기능 |
|---|---|
| `BrushingExtension` | 브러싱(범위 선택)으로 데이터 필터링 |
| `DataFilterExtension` | GPU 상의 SQL형 필터링 |
| `Fp64Extension` | 64비트 부동소수점 정밀도 |
| `PathStyleExtension` | 경로 대시 패턴 |
| `FillStyleExtension` | 채우기 패턴 커스터마이징 |
| `ClipExtension` | 임의 영역으로 클리핑 |
| `CollisionFilterExtension` | 텍스트/아이콘 충돌 감지 |
| `MaskExtension` | 마스킹/스텐실 |

**확장 훅**: `initializeState()` / `updateState()` / `getShaders()` / `draw()`

---

## 9. API 디자인 패턴

### 1. Accessor 함수 패턴

```typescript
new ScatterplotLayer({
  data: myData,
  getPosition: d => [d.lng, d.lat],   // 함수
  getRadius: 5,                        // 리터럴도 OK
  getFillColor: d => [d.r, d.g, d.b],
})
```

### 2. Update Triggers (선언적 변경 감지)

```typescript
updateTriggers: {
  getColor: ['colorMode', 'selectedId'],  // 이 값이 바뀌면 getColor 재계산
}
```

### 3. CompositeLayer (레이어 합성)

`GeoJsonLayer` = `PolygonLayer` + `PathLayer` + `ScatterplotLayer` 를 내부적으로 포함. 복잡한 시각화를 재사용 가능한 단위로 분리.

### 4. 셰이더 모듈 합성

`project`, `color`, `picking` 등 셰이더 모듈을 런타임에 주입. 확장(Extension)도 동일 방식으로 커스텀 셰이더 코드 삽입 가능.

---

## 10. 주요 의존성

| 라이브러리 | 버전 | 역할 |
|---|---|---|
| `@luma.gl/*` | 9.3.0-alpha | GPU(WebGL2/WebGPU) 추상화 |
| `@math.gl/*` | 4.1.0 | 행렬·투영 연산 |
| `@loaders.gl/*` | 4.4.0-alpha | 데이터 로딩 (CSV, Parquet, 3D Tiles) |
| `mjolnir.js` | 3.0.0 | 포인터/제스처 이벤트 캡처 |
| `earcut` | - | 다각형 삼각화 |
| `d3-hexbin` | - | 육각형 빈 생성 |
| `h3-js`, `a5-js` | - | H3/A5 공간 인덱스 |
| `s2-geometry` | - | Google S2 셀 |
| `@mapbox/tiny-sdf` | - | SDF 폰트 렌더링 |

---

## 11. 빌드 시스템

**출력 포맷**:
- `dist/index.js` — ESM
- `dist/index.cjs` — CommonJS
- `dist/index.d.ts` — TypeScript 타입
- `dist.min.js` — UMD 번들

**셰이더 관리**: GLSL(WebGL2) + WGSL(WebGPU) 이중 지원. `.glsl.ts` / `.wgsl.ts` 파일로 TS 문자열 리터럴화 → 런타임 주입.

---

## kepler.gl과의 관계

```
kepler.gl
  └── @deck.gl/layers        (레이어 렌더링)
  └── @deck.gl/geo-layers    (지리 레이어)
  └── @deck.gl/aggregation-layers (집계 레이어)
  └── @luma.gl               (WebGL 추상화)
  └── @loaders.gl            (데이터 파싱)
```

kepler.gl은 deck.gl 위에 **Redux 상태 관리 + React UI + 사용자 설정 시스템**을 얹은 고수준 애플리케이션 프레임워크다.

---

## JAH 프로젝트 연관성 메모

deck.gl은 직접 사용 가능성이 있다:

- **GeoJSON 행정구역 레이어**: `GeoJsonLayer`로 VWorld에서 받은 행정동 경계 즉시 렌더링 가능
- **ColumnLayer**: 행정동별 소득/인구 데이터를 3D 기둥으로 시각화
- **HeatmapLayer**: 인구 밀도 분포 시각화
- **H3HexagonLayer**: 격자형 도시 분석 (kepler.gl 분석의 H3 참고)
- **pydeck**: Python에서 직접 deck.gl 레이어 생성 가능 → `solver.py` 출력을 웹으로 빠르게 프로토타이핑
- **좌표계**: `LNGLAT` 모드로 VWorld GPS 데이터를 그대로 입력 가능
