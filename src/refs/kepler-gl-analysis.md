# kepler.gl 레포 분석

> 분석 날짜: 2026-03-11
> 대상: `/home/keonchae/kepler.gl` (v3.2.5)
> 출처: github.com/keplergl/kepler.gl

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 버전 | v3.2.5 |
| 라이선스 | MIT |
| 패키지 매니저 | Yarn 4.4.0 (Workspaces) |
| Node 요구사항 | >=18 |
| 빌드 도구 | Babel + ESBuild (UMD) + TypeScript (타입) |
| 패키지 구조 | Yarn Workspaces 모노레포 (22개 패키지) |

Uber에서 시작한 오픈소스 **WebGL 기반 지리 시각화 프레임워크**. React + Redux + deck.gl 조합으로 대용량 지리 데이터를 브라우저에서 GPU 가속으로 렌더링한다.

---

## 2. 전체 아키텍처

```
User Action
  │
  ▼
@kepler.gl/actions        ← Redux Action Creators
  │
  ▼
@kepler.gl/reducers       ← visState / mapState / uiState / mapStyle / providerState
  │
  ▼
@kepler.gl/processors     ← loaders.gl 래퍼 (CSV / GeoJSON / Arrow / Parquet 파싱)
  │
  ▼
@kepler.gl/layers         ← Layer 인스턴스 → deck.gl config 생성
  │
  ▼
DeckGL + MapboxGL/MapLibreGL  ← GPU 렌더링
```

### Redux 상태 구조

```
KeplerGlState[instanceId]
├── visState      : 데이터셋, 레이어, 필터, 인터랙션
├── mapState      : 카메라(위치/줌/피치/베어링), 뷰포트
├── mapStyle      : 베이스맵 스타일 (Mapbox/MapLibre 타일)
├── uiState       : 패널 열림/닫힘, 모달, 로딩 상태
└── providerState : 클라우드 저장소 (Dropbox, Carto 등)
```

멀티 맵 인스턴스 지원: `handleRegisterEntry` / `handleDeleteEntry` / `handleRenameEntry`

---

## 3. 패키지 구조 (src/)

| 패키지 | 역할 |
|---|---|
| `@kepler.gl/types` | 전체 타입 정의 |
| `@kepler.gl/constants` | 색상, 레이어 타입, 기본값 상수 |
| `@kepler.gl/common-utils` | 공통 유틸 (H3, 데이터 타입) |
| `@kepler.gl/utils` | 맵 변환, 뷰포트 프로젝션, D3 헬퍼 |
| `@kepler.gl/styles` | styled-components 테마 |
| `@kepler.gl/localization` | i18n (react-intl) |
| `@kepler.gl/table` | 데이터 테이블 컴포넌트 |
| `@kepler.gl/schemas` | 맵/데이터셋 스키마 (config 버전 관리) |
| `@kepler.gl/processors` | 데이터 로딩/파싱 파이프라인 |
| `@kepler.gl/deckgl-layers` | deck.gl 커스텀 레이어 래퍼 |
| `@kepler.gl/deckgl-arrow-layers` | Apache Arrow 전용 deck.gl 레이어 |
| `@kepler.gl/layers` | **15+ 시각화 레이어 타입** |
| `@kepler.gl/actions` | Redux 액션 크리에이터 |
| `@kepler.gl/effects` | 비주얼 이펙트 (라이팅, luma.gl 셰이더) |
| `@kepler.gl/reducers` | Redux 리듀서 |
| `@kepler.gl/components` | React UI 컴포넌트 전체 |
| `@kepler.gl/cloud-providers` | 클라우드 저장소 (Dropbox, Carto) |
| `@kepler.gl/tasks` | 비동기 태스크 (react-palm) |
| `@kepler.gl/ai-assistant` | AI 기능 (Claude / GPT / Gemini / Deepseek) |
| `@kepler.gl/duckdb` | DuckDB 쿼리 통합 |

---

## 4. 시각화 레이어 타입 (15+)

`src/layers/src/` 위치. 모두 `BaseLayer`를 상속하며 **Visual Channels** (color, size, opacity) 설정 + deck.gl config 생성을 담당.

| 레이어 | 용도 |
|---|---|
| **PointLayer** | 산점도, 점 밀도 |
| **ArcLayer** | 흐름, 연결선, 이동 경로 |
| **LineLayer** | 루트, 네트워크 |
| **GridLayer** | 격자 집계 히트맵 |
| **HexagonLayer** | 육각형 빈 집계 |
| **GeojsonLayer** | GeoJSON 피처 렌더링 |
| **ClusterLayer** | 계층적 점 클러스터링 |
| **IconLayer** | 커스텀 아이콘/마커 |
| **HeatmapLayer** | 커널 밀도 추정 |
| **H3Layer** | Uber H3 육각 셀 |
| **ScenegraphLayer** | 3D GLTF/GLB 모델 |
| **TripLayer** | 이동 궤적 애니메이션 |
| **S2GeometryLayer** | Google S2 셀 |
| **VectorTileLayer** | 벡터 타일 (MVT, PMTiles) |
| **RasterTileLayer** | 래스터 타일, WMS |
| **WMSLayer** | OGC Web Map Service |

---

## 5. 데이터 파이프라인

```
입력 파일 (CSV / GeoJSON / Arrow / Parquet / WMS)
  ↓
@loaders.gl (파싱)
  ↓
data-processor.ts  ─── 타입 분석, 스케일링, 필터링
file-handler.ts    ─── 파일 타입별 분기
  ↓
LOAD_FILES 액션 → visState.datasets 저장
  ↓
사용자: 레이어 추가 (ADD_LAYER 액션)
  ↓
Layer 인스턴스.getDeckLayerProps() → deck.gl 레이어 config
  ↓
DeckGL 렌더링
```

---

## 6. 주요 의존성

### 렌더링
| 라이브러리 | 버전 | 역할 |
|---|---|---|
| `@deck.gl/*` | 8.9.27 | GPU 레이어 렌더링 |
| `@luma.gl/*` | 8.5.21 | WebGL 추상화 |
| `mapbox-gl` | 1.13.1 | 베이스맵 |
| `maplibre-gl` | 3.6.2 | 오픈소스 베이스맵 |
| `react-map-gl` | 7.1.6 | React 맵 래퍼 |

### 데이터 처리
| 라이브러리 | 버전 | 역할 |
|---|---|---|
| `@loaders.gl/*` | 4.3.2 | CSV/Parquet/Arrow/GIS 파싱 |
| `apache-arrow` | >=15.0.0 | Arrow 컬럼형 포맷 |
| `@turf/*` | - | 지리 공간 연산 |
| `h3-js` | 3.1.0 | Uber H3 육각형 |
| `s2-geometry` | 1.2.10 | Google S2 셀 |
| `supercluster` | 7.1.0 | 점 클러스터링 |

### 색상/스케일
| 라이브러리 | 역할 |
|---|---|
| `d3-scale`, `d3-array` | 데이터 스케일링 |
| `chroma-js` | 색상 공간 변환, 팔레트 |
| `colorbrewer` | 카토그래피 색상 팔레트 |

### AI
| 라이브러리 | 역할 |
|---|---|
| `@ai-sdk/anthropic` | Claude 연동 |
| `@ai-sdk/google` | Gemini 연동 |
| `@openassistant/*` | 모듈형 AI 어시스턴트 |
| `ollama-ai-provider-v2` | 로컬 LLM |

---

## 7. 빌드 시스템

| 명령 | 도구 | 출력 |
|---|---|---|
| `yarn build` | Babel | `dist/` |
| `yarn build:umd` | ESBuild | `umd/` |
| `yarn build:types` | tsc | 타입 선언 |
| `yarn analyze:bundle` | Webpack Bundle Analyzer | - |

---

## 8. 컴포넌트 계층

```
<KeplerGL>
├── <MapContainer>          ← DeckGL + react-map-gl
├── <SidePanel>             ← 레이어/필터 편집기
├── <BottomWidget>          ← 범례, 인터랙션
├── <ModalContainer>        ← 내보내기, 저장, 데이터 불러오기
├── <NotificationPanel>     ← 오류, 진행 알림
└── <PlotContainer>         ← 히스토그램, 타임라인 애니메이션
```

---

## 9. 테스트

| 항목 | 내용 |
|---|---|
| Jest | 단위 테스트 (`src/**/*.spec.ts`, jsdom) |
| Tape | Node.js 통합 테스트 (`test/node/**`) |
| Puppeteer | 브라우저 E2E 테스트 (`test/browser/**`) |
| 커버리지 | Istanbul + NYC |

---

## 10. 예제 앱 (examples/)

`demo-app`, `custom-reducer`, `custom-theme`, `node-app` 등 10개 데모 앱 제공.

---

## JAH 프로젝트 연관성 메모

kepler.gl은 **웹 기반** 시각화이므로 Rhino/Grasshopper 기반 JAH와 직접 통합은 어렵다.
그러나 다음 측면에서 참고 가치가 있다:

- **H3 헥사곤 기반 도시 집계** → Grasshopper에서 유사 격자 집계 구현 시 참고
- **Color scale 설계** (`chroma-js` + `colorbrewer`) → `visualizer.py`의 메시 컬러 매핑에 응용
- **GeoJSON 데이터 파이프라인** → VWorld API 결과를 kepler.gl로 직접 시각화 가능 (웹 프로토타이핑)
- **Trip/Arc 레이어** → 통근/이동 데이터 시각화 레퍼런스
