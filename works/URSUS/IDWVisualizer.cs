// Grasshopper Script Instance
// IDW 공간 보간 + 단일 외곽선(GeoUnion 출력) 기반 Mesh 시각화
#region Usings
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;

using Rhino;
using Rhino.Geometry;

using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Grasshopper.Kernel.Types;
#endregion

public class Script_Instance : GH_ScriptInstance
{
    // ─────────────────────────────────────────────────────────────────────
    //  ENTRY POINT
    //
    //  입력:  boundary    GeoUnion이 반환한 단일 외곽선 (Curve)
    //         centroids   행정동 중심점 (List<Point3d>)
    //         values      스칼라 값 - avg_incomes 등 (List<double>)
    //         resolution  Mesh 최대 엣지 길이 (double)
    //         power       IDW 지수 p, 기본 2.0 (double)
    //         heightScale Z 높이 배율 (double)
    //         legendSteps 범례 단계 수, 기본 8 (int)
    //         colorStyle  색상 스타일 (int, 0=Custom 1=BlueRed 2=Heatmap
    //                       3=Spectral 4=Viridis 5=Diverging 6=Grayscale)
    //         colorLow    colorStyle=0 일 때 최솟값 색상 (Color)
    //         colorHigh   colorStyle=0 일 때 최댓값 색상 (Color)
    //
    //  출력:  mesh        Z 변위 + 컬러 메시 (Mesh)
    //         flatMesh    Z=0, 컬러만 - 지도 오버레이용 (Mesh)
    //         minVal      범례 최솟값 (double)
    //         maxVal      범례 최댓값 (double)
    //         legendMesh  범례 그라디언트 바 (Mesh)
    //         legendDots  범례 값 레이블 (List<TextDot>)
    // ─────────────────────────────────────────────────────────────────────
    private void RunScript(
        Curve         boundary,
        List<Point3d> centroids,
        List<double>  values,
        double        resolution,
        double        power,
        double        heightScale,
        double        edgeFalloff,
        double        heightRatio,
        int           legendSteps,
        int           colorStyle,
        Color         colorLow,
        Color         colorHigh,
        ref object    mesh,
        ref object    flatMesh,
        ref object    minVal,
        ref object    maxVal,
        ref object    legendMesh,
        ref object    legendDots)
    {
        try
        {
        // ── 입력 확인 ─────────────────────────────────────────────────────
        int nanCount = values?.Count(v => double.IsNaN(v) || double.IsInfinity(v)) ?? 0;
        Print($"[0] boundary={boundary != null}, centroids={centroids?.Count ?? -1}, values={values?.Count ?? -1}, NaN/Inf={nanCount}");

        if (boundary == null)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "boundary가 null입니다."); return; }
        if (centroids == null || centroids.Count == 0)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "centroids가 비어 있습니다."); return; }
        if (values == null || values.Count == 0)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "values가 비어 있습니다."); return; }
        if (centroids.Count != values.Count)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "centroids와 values의 개수가 다릅니다."); return; }

        // ── 파라미터 기본값 ───────────────────────────────────────────────
        if (resolution   <= 0) resolution   = 100.0;
        if (power        <= 0) power        = 3.0;
        if (heightScale  <= 0) heightScale  = 0.5;
        if (legendSteps  <= 1) legendSteps  = 8;
        if (colorLow.A   == 0) colorLow     = Color.FromArgb(44,  123, 182);
        if (colorHigh.A  == 0) colorHigh    = Color.FromArgb(215,  25,  28);
        if (edgeFalloff  <= 0) edgeFalloff  = 2.0;   // 기본: smoothstep 유사
        if (heightRatio  <= 0) heightRatio  = 0.25;  // 기본: bboxWidth * 0.25

        // ── 파이프라인 ────────────────────────────────────────────────────
        var field   = new SpatialField(centroids, values);
        var mapper  = ColorMapper.FromStyle(colorStyle, colorLow, colorHigh);
        var builder = new MeshBuilder(field, mapper, power, heightScale, resolution, edgeFalloff, heightRatio);

        Print($"[1] MinVal={field.MinValue:F0}, MaxVal={field.MaxValue:F0}, colorStyle={mapper.StyleName}");

        var (elevMesh, flatResult) = builder.Build(boundary);
        Print($"[2] {builder.DebugLog}");

        if (elevMesh.Vertices.Count == 0)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "생성된 Mesh가 비어 있습니다."); return; }

        // ── 범례 위치 계산 (bbox 오른쪽) ──────────────────────────────────
        BoundingBox bbox  = elevMesh.GetBoundingBox(false);
        double      bboxW = bbox.Max.X - bbox.Min.X;
        double      bboxH = bbox.Max.Y - bbox.Min.Y;
        Point3d     anchor = new Point3d(bbox.Max.X + bboxW * 0.02, bbox.Min.Y, 0.0);
        double      legendW = Math.Max(bboxW * 0.03, 100.0);

        var legendBuilder = new LegendBuilder(field, mapper, anchor, legendW, bboxH, legendSteps);

        // ── 출력 ──────────────────────────────────────────────────────────
        mesh       = elevMesh;
        flatMesh   = flatResult;
        minVal     = field.MinValue;
        maxVal     = field.MaxValue;
        legendMesh = legendBuilder.BuildMesh();
        legendDots = legendBuilder.BuildDots();

        Print("[3] 완료.");
        }
        catch (Exception ex)
        {
            Print($"[ERR] {ex.GetType().Name}: {ex.Message}\n{ex.StackTrace}");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ex.Message);
        }
    }


    // ═════════════════════════════════════════════════════════════════════
    //  CLASS: SpatialField
    //  알려진 (Point, Value) 쌍을 보관하고 IDW 보간을 수행한다.
    // ═════════════════════════════════════════════════════════════════════
    class SpatialField
    {
        public readonly List<Point3d> Points;
        public readonly List<double>  Values;
        public readonly double        MinValue;
        public readonly double        MaxValue;

        public SpatialField(List<Point3d> points, List<double> values)
        {
            Points   = points;
            Values   = values;
            MinValue = values.Min();
            MaxValue = values.Max();
        }

        /// IDW: F(q) = Σ[vᵢ / dᵢᵖ] / Σ[1 / dᵢᵖ]
        public double IDW(Point3d query, double power)
        {
            double num = 0.0, den = 0.0;
            for (int i = 0; i < Points.Count; i++)
            {
                double d = query.DistanceTo(Points[i]);
                if (d < 1e-10) return Values[i];
                double w = 1.0 / Math.Pow(d, power);
                num += w * Values[i];
                den += w;
            }
            double result = den < 1e-12 ? 0.0 : num / den;
            return double.IsNaN(result) || double.IsInfinity(result) ? 0.0 : result;
        }

        public double Normalize(double v)
        {
            double range = MaxValue - MinValue;
            return range < 1e-12 ? 0.5 : (v - MinValue) / range;
        }

        public double Normalize(double v, double outMin, double outMax)
            => outMin + Normalize(v) * (outMax - outMin);
    }


    // ═════════════════════════════════════════════════════════════════════
    //  CLASS: ColorMapper
    //  N개 color stop을 균등 간격으로 배치하고 t(0~1) → Color 보간
    //
    //  colorStyle:
    //    0 = Custom     colorLow → colorHigh (사용자 지정)
    //    1 = BlueRed    Blue → Red
    //    2 = Heatmap    Green → Yellow → Red
    //    3 = Spectral   Blue → Cyan → Green → Yellow → Red
    //    4 = Viridis    Purple → Blue → Teal → Green → Yellow
    //    5 = Diverging  Blue → White → Red
    //    6 = Grayscale  White → Black
    // ═════════════════════════════════════════════════════════════════════
    class ColorMapper
    {
        private readonly Color[] _stops;
        public  readonly string  StyleName;

        public ColorMapper(Color[] stops, string name) { _stops = stops; StyleName = name; }

        public static ColorMapper FromStyle(int style, Color customLow, Color customHigh)
        {
            switch (style)
            {
                case 1:  return new ColorMapper(new[]{ C(44,123,182), C(215,25,28) }, "BlueRed");
                case 2:  return new ColorMapper(new[]{ C(0,128,0), C(255,255,0), C(255,0,0) }, "Heatmap");
                case 3:  return new ColorMapper(new[]{ C(0,0,200), C(0,200,200), C(0,200,0), C(255,255,0), C(220,0,0) }, "Spectral");
                case 4:  return new ColorMapper(new[]{ C(68,1,84), C(58,82,139), C(32,144,140), C(94,201,98), C(253,231,37) }, "Viridis");
                case 5:  return new ColorMapper(new[]{ C(44,123,182), C(255,255,255), C(215,25,28) }, "Diverging");
                case 6:  return new ColorMapper(new[]{ C(255,255,255), C(0,0,0) }, "Grayscale");
                default: return new ColorMapper(new[]{ customLow, customHigh }, "Custom");
            }
        }

        private static Color C(int r, int g, int b) => Color.FromArgb(r, g, b);

        public Color Map(double t)
        {
            t = Math.Max(0.0, Math.Min(1.0, t));
            double scaled = t * (_stops.Length - 1);
            int    lo     = (int)scaled;
            int    hi     = Math.Min(lo + 1, _stops.Length - 1);
            double lt     = scaled - lo;
            return Color.FromArgb(
                Lerp(_stops[lo].R, _stops[hi].R, lt),
                Lerp(_stops[lo].G, _stops[hi].G, lt),
                Lerp(_stops[lo].B, _stops[hi].B, lt));
        }

        private static int Lerp(int a, int b, double t)
            => Math.Max(0, Math.Min(255, (int)Math.Round(a + (b - a) * t)));
    }


    // ═════════════════════════════════════════════════════════════════════
    //  CLASS: MeshBuilder
    //  GeoUnion이 반환한 단일 외곽선 Curve → Mesh 변환 후
    //  IDW 값을 Color로, boundary 거리 감쇠(smoothstep)를 Z 변위로 적용한다.
    //
    //  Z = Normalize(IDW) * heightScale * smoothstep(dist / maxDist)
    //    → 경계에서 Z=0, 내부로 갈수록 자연스럽게 솟아오르는 산 형태
    // ═════════════════════════════════════════════════════════════════════
    class MeshBuilder
    {
        private readonly SpatialField _field;
        private readonly ColorMapper  _mapper;
        private readonly double       _power;
        private readonly double       _heightScale;
        private readonly double       _maxEdgeLen;
        private readonly double       _edgeFalloff;  // 경계 감쇠 지수: 낮을수록 완만, 높을수록 급격
        private readonly double       _heightRatio;  // Z 최대 높이 = bboxWidth * heightRatio

        public string DebugLog { get; private set; } = "";

        private const double DEFAULT_TOL = 0.001;

        public MeshBuilder(SpatialField field, ColorMapper mapper,
                           double power, double heightScale, double maxEdgeLen,
                           double edgeFalloff, double heightRatio)
        {
            _field       = field;
            _mapper      = mapper;
            _power       = power;
            _heightScale = heightScale;
            _maxEdgeLen  = maxEdgeLen;
            _edgeFalloff = edgeFalloff;
            _heightRatio = heightRatio;
        }

        public (Mesh elevated, Mesh flat) Build(Curve boundary)
        {
            double tol = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? DEFAULT_TOL;

            // ── Curve → Brep → 단일 baseMesh ─────────────────────────────
            Brep[] breps = Brep.CreatePlanarBreps(boundary, tol);
            if (breps == null || breps.Length == 0)
            {
                DebugLog = "Brep 생성 실패";
                return (new Mesh(), new Mesh());
            }

            var mp       = new MeshingParameters {
                MaximumEdgeLength = _maxEdgeLen,
                MinimumEdgeLength = _maxEdgeLen * 0.1,
                JaggedSeams       = false,
                RefineGrid        = true,
            };
            var baseMesh = new Mesh();
            foreach (Brep brep in breps)
            {
                Mesh[] meshes = Mesh.CreateFromBrep(brep, mp);
                if (meshes != null) foreach (Mesh m in meshes) baseMesh.Append(m);
            }
            baseMesh.Compact();

            int n = baseMesh.Vertices.Count;
            if (n == 0) { DebugLog = "Mesh 버텍스 없음"; return (new Mesh(), new Mesh()); }

            // Z 정규화 기준: boundary bbox width
            var    bbox     = boundary.GetBoundingBox(false);
            double bboxWidth = bbox.IsValid ? (bbox.Max.X - bbox.Min.X) : 1.0;

            // ── 버텍스별 IDW + boundary 거리 계산 (단일 패스) ────────────
            var    interpValues = new double[n];
            var    colors       = new Color[n];
            var    dists        = new double[n];
            double maxDist      = 0.0;

            for (int vi = 0; vi < n; vi++)
            {
                Point3d q   = baseMesh.Vertices.Point3dAt(vi);
                Point3d q2d = new Point3d(q.X, q.Y, 0.0);

                double f         = _field.IDW(q2d, _power);
                interpValues[vi] = f;
                colors[vi]       = _mapper.Map(_field.Normalize(f));

                double t;
                boundary.ClosestPoint(q2d, out t);
                Point3d closest = boundary.PointAt(t);
                double  d = Math.Sqrt(
                    (q.X - closest.X) * (q.X - closest.X) +
                    (q.Y - closest.Y) * (q.Y - closest.Y));
                dists[vi] = d;
                if (d > maxDist) maxDist = d;
            }

            // ── flat mesh: Z=0, 컬러만 ───────────────────────────────────
            Mesh flat = baseMesh.DuplicateMesh();
            flat.TextureCoordinates.Clear();
            ApplyColors(flat, colors);
            flat.Normals.ComputeNormals();
            flat.FaceNormals.ComputeFaceNormals();

            // ── elevated mesh: Z = IDW_height * smoothstep(dist/maxDist) ─
            Mesh elevated = baseMesh.DuplicateMesh();
            elevated.TextureCoordinates.Clear();
            for (int vi = 0; vi < n; vi++)
            {
                Point3d vd = baseMesh.Vertices.Point3dAt(vi);
                double  dt = maxDist > 0 ? Math.Min(dists[vi] / maxDist, 1.0) : 1.0;
                double  s  = Math.Pow(dt, _edgeFalloff);  // 감쇠: 낮을수록 완만, 높을수록 경계 근처 급격
                double  zd = _field.Normalize(interpValues[vi], 0.0, bboxWidth * _heightRatio)
                             * _heightScale * s;
                if (double.IsNaN(zd) || double.IsInfinity(zd)) zd = 0.0;
                elevated.Vertices.SetVertex(vi, new Point3d(vd.X, vd.Y, zd));
            }
            ApplyColors(elevated, colors);
            elevated.Normals.ComputeNormals();
            elevated.FaceNormals.ComputeFaceNormals();

            DebugLog = $"Verts={n} Faces={baseMesh.Faces.Count} bboxW={bboxWidth:F0}m maxDist={maxDist:F0}m | "
                     + $"elev: Valid={elevated.IsValid} flat: Valid={flat.IsValid}";
            return (elevated, flat);
        }

        private static void ApplyColors(Mesh mesh, Color[] colors)
        {
            mesh.VertexColors.CreateMonotoneMesh(Color.White);
            for (int i = 0; i < colors.Length; i++)
                mesh.VertexColors.SetColor(i, colors[i]);
        }
    }


    // ═════════════════════════════════════════════════════════════════════
    //  CLASS: LegendBuilder
    //  그라디언트 컬러 바(Mesh)와 값 레이블(TextDot)로 구성된 범례를 생성한다.
    // ═════════════════════════════════════════════════════════════════════
    class LegendBuilder
    {
        private readonly SpatialField _field;
        private readonly ColorMapper  _mapper;
        private readonly Point3d      _anchor;
        private readonly double       _width;
        private readonly double       _height;
        private readonly int          _steps;

        public LegendBuilder(SpatialField field, ColorMapper mapper,
                             Point3d anchor, double width, double height, int steps)
        {
            _field  = field;
            _mapper = mapper;
            _anchor = anchor;
            _width  = width;
            _height = height;
            _steps  = steps;
        }

        /// 수직 그라디언트 컬러 바 Mesh (아래=min, 위=max)
        public Mesh BuildMesh()
        {
            var    mesh  = new Mesh();
            var    cols  = new List<Color>();
            double stepH = _height / _steps;

            for (int i = 0; i <= _steps; i++)
            {
                double t = (double)i / _steps;
                Color  c = _mapper.Map(t);
                float  y = (float)(_anchor.Y + i * stepH);
                mesh.Vertices.Add((float)_anchor.X,            y, 0f);
                mesh.Vertices.Add((float)(_anchor.X + _width), y, 0f);
                cols.Add(c);
                cols.Add(c);
            }
            for (int i = 0; i < _steps; i++)
            {
                int b = i * 2;
                mesh.Faces.AddFace(b, b + 2, b + 3, b + 1);
            }
            mesh.VertexColors.CreateMonotoneMesh(Color.White);
            for (int i = 0; i < cols.Count; i++)
                mesh.VertexColors.SetColor(i, cols[i]);
            mesh.Normals.ComputeNormals();
            return mesh;
        }

        /// 범례 값 레이블 TextDot 목록
        public List<TextDot> BuildDots()
        {
            var    dots   = new List<TextDot>();
            double stepH  = _height / _steps;
            double labelX = _anchor.X + _width * 1.4;

            for (int i = 0; i <= _steps; i++)
            {
                double t   = (double)i / _steps;
                double val = _field.MinValue + t * (_field.MaxValue - _field.MinValue);
                double y   = _anchor.Y + i * stepH;
                var    dot = new TextDot(val.ToString("N0"), new Point3d(labelX, y, 0.0));
                dot.FontHeight = 12;
                dots.Add(dot);
            }
            return dots;
        }
    }
}
