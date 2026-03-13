// Grasshopper Script Instance
// IDW 공간 보간 + 행정동 경계 기반 Mesh 시각화
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
    //  입력:  geometries  행정동 경계 폴리곤 (List<Curve>)
    //         centroids   행정동 중심점 (List<Point3d>)
    //         values      스칼라 값 - avg_incomes 등 (List<double>)
    //         resolution  Mesh 최대 엣지 길이, 보간 해상도 (double)
    //         power       IDW 지수 p, 기본 2.0 (double)
    //         heightScale Z 높이 배율 (double)
    //         colorLow    최솟값 색상 (Color)
    //         colorHigh   최댓값 색상 (Color)
    //         legendSteps 범례 단계 수, 기본 8 (int)
    //
    //  출력:  mesh        Z 변위 + 컬러 메시 (Mesh)
    //         flatMesh    Z=0, 컬러만 - 지도 오버레이용 (Mesh)
    //         minVal      범례 최솟값 (double)
    //         maxVal      범례 최댓값 (double)
    //         legendMesh  범례 그라디언트 바 (Mesh)
    //         legendDots  범례 값 레이블 (List<TextDot>)
    // ─────────────────────────────────────────────────────────────────────
    private void RunScript(
        List<Curve>   geometries,
        List<Point3d> centroids,
        List<double>  values,
        double        resolution,
        double        power,
        double        heightScale,
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
        // ── Step 0: 입력 수신 확인 ─────────────────────────────────────
        Print($"[0] geometries={geometries?.Count ?? -1}, centroids={centroids?.Count ?? -1}, values={values?.Count ?? -1}");

        // ── 입력 검증 ────────────────────────────────────────────────────
        if (geometries == null || geometries.Count == 0)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "geometries가 비어 있습니다."); return; }
        if (centroids == null || centroids.Count == 0)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "centroids가 비어 있습니다.");  return; }
        if (values == null || values.Count == 0)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "values가 비어 있습니다.");     return; }
        if (centroids.Count != values.Count)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "centroids와 values의 개수가 다릅니다."); return; }

        int nanCount = values.Count(v => double.IsNaN(v) || double.IsInfinity(v));
        Print($"[1] 검증 통과. centroids={centroids.Count}, values={values.Count}, NaN/Inf={nanCount}");

        // ── 파라미터 기본값 ──────────────────────────────────────────────
        if (resolution  <= 0)        resolution  = 500.0;
        if (power       <= 0)        power       = 1.0;
        if (heightScale <= 0)        heightScale = 0.5;
        if (legendSteps <= 1)        legendSteps = 8;
        if (colorLow.A  == 0)        colorLow    = Color.FromArgb(44,  123, 182);
        if (colorHigh.A == 0)        colorHigh   = Color.FromArgb(215,  25,  28);

        // ── 파이프라인 ───────────────────────────────────────────────────
        var field   = new SpatialField(centroids, values);
        var mapper  = ColorMapper.FromStyle(colorStyle, colorLow, colorHigh);
        Print($"[1b] colorStyle={colorStyle} → {mapper.StyleName}");
        var builder = new DistrictMeshBuilder(field, mapper, power, heightScale, resolution);

        Print($"[2] SpatialField/Builder 생성 완료. MinVal={field.MinValue:F0}, MaxVal={field.MaxValue:F0}");

        Mesh elevMesh, flatResult;
        int dbgNull, dbgBrepFail, dbgMeshFail, dbgOk;

        builder.Build(geometries, out elevMesh, out flatResult,
                      out dbgNull, out dbgBrepFail, out dbgMeshFail, out dbgOk);

        Print($"[3] Build 완료: null={dbgNull} | BrepFail={dbgBrepFail} | MeshFail={dbgMeshFail} | OK={dbgOk}");
        Print($"[3] elevMesh: Valid={elevMesh.IsValid} Verts={elevMesh.Vertices.Count} Faces={elevMesh.Faces.Count} VNorm={elevMesh.Normals.Count} FaceNorm={elevMesh.FaceNormals.Count} Colors={elevMesh.VertexColors.Count}");
        Print($"[3] flatMesh: Valid={flatResult.IsValid} Verts={flatResult.Vertices.Count} Faces={flatResult.Faces.Count} VNorm={flatResult.Normals.Count} FaceNorm={flatResult.FaceNormals.Count} Colors={flatResult.VertexColors.Count}");
        Print(builder._dbgLog);  // 첫 번째 district elevPart 개별 상태

        if (elevMesh.Vertices.Count == 0)
        { AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "생성된 Mesh가 비어 있습니다. geometries를 확인하세요."); return; }

        // ── 범례 위치 계산 (elevated mesh bbox 오른쪽) ───────────────────
        BoundingBox bbox = elevMesh.GetBoundingBox(false);
        double bboxW     = bbox.Max.X - bbox.Min.X;
        double bboxH     = bbox.Max.Y - bbox.Min.Y;
        double legendH   = bboxH;
        double legendW   = Math.Max(bboxW * 0.03, 100.0);
        double legendGap = bboxW * 0.02;
        Point3d anchor   = new Point3d(bbox.Max.X + legendGap, bbox.Min.Y, 0.0);

        var legendBuilder = new LegendBuilder(field, mapper, anchor, legendW, legendH, legendSteps);

        // ── 출력 ─────────────────────────────────────────────────────────
        mesh       = elevMesh;
        flatMesh   = flatResult;
        minVal     = field.MinValue;
        maxVal     = field.MaxValue;
        legendMesh = legendBuilder.BuildMesh();
        legendDots = legendBuilder.BuildDots();

        Print("[4] 완료.");
        } // end try
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
        public readonly double MinValue;
        public readonly double MaxValue;

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

        /// 값을 [0, 1]로 정규화
        public double Normalize(double v)
        {
            double range = MaxValue - MinValue;
            if (range < 1e-12) return 0.5;
            return (v - MinValue) / range;
        }

        /// 값을 [outMin, outMax] 범위로 정규화
        public double Normalize(double v, double outMin, double outMax)
        {
            return outMin + Normalize(v) * (outMax - outMin);
        }
    }


    // ═════════════════════════════════════════════════════════════════════
    //  CLASS: ColorMapper
    //  N개 color stop을 균등 간격으로 배치하고 t(0~1) → Color 보간
    //
    //  colorStyle:
    //    0 = Custom        colorLow → colorHigh (2-stop, 사용자 지정)
    //    1 = BlueRed       Blue → Red (diverging)
    //    2 = Heatmap       Green → Yellow → Red
    //    3 = Spectral      Blue → Cyan → Green → Yellow → Red
    //    4 = Viridis       Purple → Blue → Teal → Green → Yellow
    //    5 = Diverging     Blue → White → Red (중앙이 흰색)
    //    6 = Grayscale     White → Black
    // ═════════════════════════════════════════════════════════════════════
    class ColorMapper
    {
        private readonly Color[] _stops;
        public  readonly string  StyleName;

        public ColorMapper(Color[] stops, string name)
        {
            _stops    = stops;
            StyleName = name;
        }

        public static ColorMapper FromStyle(int style, Color customLow, Color customHigh)
        {
            switch (style)
            {
                case 1: return new ColorMapper(new[]{ C(44,123,182), C(215,25,28) }, "BlueRed");
                case 2: return new ColorMapper(new[]{ C(0,128,0), C(255,255,0), C(255,0,0) }, "Heatmap");
                case 3: return new ColorMapper(new[]{ C(0,0,200), C(0,200,200), C(0,200,0), C(255,255,0), C(220,0,0) }, "Spectral");
                case 4: return new ColorMapper(new[]{ C(68,1,84), C(58,82,139), C(32,144,140), C(94,201,98), C(253,231,37) }, "Viridis");
                case 5: return new ColorMapper(new[]{ C(44,123,182), C(255,255,255), C(215,25,28) }, "Diverging");
                case 6: return new ColorMapper(new[]{ C(255,255,255), C(0,0,0) }, "Grayscale");
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

            int r = (int)Math.Round(_stops[lo].R + (_stops[hi].R - _stops[lo].R) * lt);
            int g = (int)Math.Round(_stops[lo].G + (_stops[hi].G - _stops[lo].G) * lt);
            int b = (int)Math.Round(_stops[lo].B + (_stops[hi].B - _stops[lo].B) * lt);
            return Color.FromArgb(
                Math.Max(0, Math.Min(255, r)),
                Math.Max(0, Math.Min(255, g)),
                Math.Max(0, Math.Min(255, b)));
        }
    }


    // ═════════════════════════════════════════════════════════════════════
    //  CLASS: DistrictMeshBuilder
    //  행정동 경계 Curve → Mesh 변환 후 IDW 값을 Z 변위와 Color로 적용한다.
    // ═════════════════════════════════════════════════════════════════════
    class DistrictMeshBuilder
    {
        private readonly SpatialField _field;
        private readonly ColorMapper  _mapper;
        private readonly double       _power;
        private readonly double       _heightScale;
        private readonly double       _maxEdgeLen;
        public  string               _dbgLog = "";

        private const double DEFAULT_TOLERANCE = 0.001;

        public DistrictMeshBuilder(
            SpatialField field, ColorMapper mapper,
            double power, double heightScale, double maxEdgeLen)
        {
            _field       = field;
            _mapper      = mapper;
            _power       = power;
            _heightScale = heightScale;
            _maxEdgeLen  = maxEdgeLen;
        }

        public void Build(List<Curve> boundaries, out Mesh elevated, out Mesh flat,
                          out int dbgNull, out int dbgBrepFail, out int dbgMeshFail, out int dbgOk)
        {
            elevated    = new Mesh();
            flat        = new Mesh();
            dbgNull     = 0;
            dbgBrepFail = 0;
            dbgMeshFail = 0;
            dbgOk       = 0;

            var mp  = BuildMeshingParameters();
            double tol = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? DEFAULT_TOLERANCE;

            // 전체 geometry bbox width → Z 정규화 기준
            var combinedBbox = BoundingBox.Empty;
            foreach (Curve c in boundaries)
                if (c != null) combinedBbox.Union(c.GetBoundingBox(false));
            double bboxWidth = combinedBbox.IsValid ? (combinedBbox.Max.X - combinedBbox.Min.X) : 1.0;
            // [검증] Print는 RunScript 레벨에서 불가하므로 _dbgLog에 기록
            _dbgLog = $"[3a] bboxWidth={bboxWidth:F0} | ";

            foreach (Curve boundary in boundaries)
            {
                if (boundary == null) { dbgNull++; continue; }

                Brep[] planarBreps = Brep.CreatePlanarBreps(boundary, tol);
                if (planarBreps == null || planarBreps.Length == 0) { dbgBrepFail++; continue; }

                foreach (Brep brep in planarBreps)
                {
                    Mesh districtMesh = MeshFromBrep(brep, mp);
                    if (districtMesh == null || districtMesh.Vertices.Count == 0) { dbgMeshFail++; continue; }

                    int n = districtMesh.Vertices.Count;
                    var interpValues = new double[n];
                    var colors       = new Color[n];

                    for (int vi = 0; vi < n; vi++)
                    {
                        Point3f vf = districtMesh.Vertices[vi];
                        Point3d q  = new Point3d(vf.X, vf.Y, 0.0);
                        double f   = _field.IDW(q, _power);
                        double t   = _field.Normalize(f);
                        interpValues[vi] = f;
                        colors[vi]       = _mapper.Map(t);
                    }

                    // elevated: DuplicateMesh → texcoords 제거 → Z 적용(double precision) → Compact
                    Mesh elevPart = districtMesh.DuplicateMesh();
                    elevPart.TextureCoordinates.Clear();
                    // Z = Normalize(idw, 0, bboxWidth) × heightScale
                    // double precision Point3dAt + SetVertex(double) 사용
                    for (int vi = 0; vi < n; vi++)
                    {
                        Point3d vd = districtMesh.Vertices.Point3dAt(vi);
                        double  zd = _field.Normalize(interpValues[vi], 0.0, bboxWidth/4) * _heightScale;
                        if (double.IsNaN(zd) || double.IsInfinity(zd)) zd = 0.0;
                        elevPart.Vertices.SetVertex(vi, vd.X, vd.Y, zd);
                    }
                    // [검증] 첫 district: elevPart 개별 IsValid + bboxWidth 확인
                    if (dbgOk == 0)
                        _dbgLog += $"elevPart[0]: Valid={elevPart.IsValid} HasDblPrec={elevPart.Vertices.UseDoublePrecisionVertices}";
                    elevPart.Compact();
                    ApplyVertexColors(elevPart, colors);
                    elevPart.Normals.ComputeNormals();
                    elevated.Append(elevPart);

                    // flat: DuplicateMesh → texcoords 제거 → Compact
                    Mesh flatPart = districtMesh.DuplicateMesh();
                    flatPart.TextureCoordinates.Clear();
                    flatPart.Compact();
                    ApplyVertexColors(flatPart, colors);
                    flatPart.Normals.ComputeNormals();
                    flat.Append(flatPart);

                    dbgOk++;
                }
            }

            elevated.Compact();
            elevated.FaceNormals.ComputeFaceNormals();
            elevated.Normals.ComputeNormals();
            flat.Compact();
            flat.FaceNormals.ComputeFaceNormals();
            flat.Normals.ComputeNormals();
        }

        private MeshingParameters BuildMeshingParameters()
        {
            var mp = new MeshingParameters();
            mp.MaximumEdgeLength = _maxEdgeLen;
            mp.MinimumEdgeLength = _maxEdgeLen * 0.1;
            mp.JaggedSeams       = false;
            mp.RefineGrid        = true;
            return mp;
        }

        private static Mesh MeshFromBrep(Brep brep, MeshingParameters mp)
        {
            Mesh[] meshes = Mesh.CreateFromBrep(brep, mp);
            if (meshes == null || meshes.Length == 0) return null;
            var combined = new Mesh();
            foreach (Mesh m in meshes) combined.Append(m);
            combined.Compact();
            return combined;
        }

        private static void ApplyVertexColors(Mesh mesh, Color[] colors)
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

        public LegendBuilder(
            SpatialField field, ColorMapper mapper,
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
            var mesh  = new Mesh();
            var cols  = new List<Color>();
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
            var dots  = new List<TextDot>();
            double stepH  = _height / _steps;
            double labelX = _anchor.X + _width * 1.4;

            for (int i = 0; i <= _steps; i++)
            {
                double t   = (double)i / _steps;
                double val = _field.MinValue + t * (_field.MaxValue - _field.MinValue);
                double y   = _anchor.Y + i * stepH;
                var dot    = new TextDot(val.ToString("N0"), new Point3d(labelX, y, 0.0));
                dot.FontHeight = 12;
                dots.Add(dot);
            }
            return dots;
        }
    }
}
