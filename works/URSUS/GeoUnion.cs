// Grasshopper Script Instance
// 행정동 경계 Curve 리스트 → Boolean Union → 단일 외곽선
//
// Rust shapely_rs의 clean_union 파이프라인 참조:
//   1. 유효 curve 수집
//   2. CCW 정렬 + outward offset으로 인접 구역 사이의 틈 폐합 (edge-snap 대체)
//   3. Curve.CreateBooleanUnion → 실패 시 Brep 경유 fallback
//   4. 결과 curve 반환
#region Usings
using System;
using System.Collections.Generic;
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
    //  입력:  geometries   행정동 경계 Curve 목록 (List<Curve>)
    //         snapTol      인접 구역 간격 폐합 허용 오차 (double, 기본 5.0 = 5m)
    //                      Rust의 polygon_snap_distance에 대응
    //
    //  출력:  unionCurves  Boolean Union 결과 외곽선 (List<Curve>)
    //         dbg          디버그 요약 (string)
    // ─────────────────────────────────────────────────────────────────────
    private void RunScript(
        List<Curve> geometries,
        double      snapTol,
        ref object  unionCurves,
        ref object  dbg)
    {
        try
        {
        double tol = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001;
        if (snapTol <= 0) snapTol = 5.0;

        Print($"[0] 입력={geometries?.Count ?? -1}, snapTol={snapTol}");

        // ── 1. 유효한 닫힌 Curve 수집 ─────────────────────────────────────
        var valid = new List<Curve>();
        foreach (Curve c in geometries ?? Enumerable.Empty<Curve>())
            if (c != null && c.IsClosed) valid.Add(c.DuplicateCurve());

        Print($"[1] 유효 curve={valid.Count}");

        if (valid.Count == 0)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "유효한 닫힌 Curve가 없습니다.");
            return;
        }

        // ── 2. CCW 정렬 + outward offset → gap 폐합 ───────────────────────
        //  Rust: snap_close_polygons() — 인접 polygon 꼭짓점을 tolerance 내에서 스냅
        //  C# 대체: 각 curve를 snapTol만큼 외부로 부풀려 gap을 물리적으로 닫음
        var expanded = new List<Curve>();
        int offsetFail = 0;
        foreach (Curve c in valid)
        {
            // CCW 방향 보장: Rhino에서 평면 위 양수 offset = 외부 방향
            if (c.ClosedCurveOrientation(Plane.WorldXY) == CurveOrientation.Clockwise)
                c.Reverse();

            Curve[] offs = c.Offset(
                Plane.WorldXY, snapTol, tol, CurveOffsetCornerStyle.Sharp);

            if (offs != null && offs.Length > 0)
            {
                // offset 조각들을 join → 닫힌 curve 선택
                Curve[] joined = Curve.JoinCurves(offs, tol);
                Curve chosen   = joined?.FirstOrDefault(j => j != null && j.IsClosed);

                // join 실패 시 bbox 가장 큰 조각 사용
                if (chosen == null)
                {
                    chosen = offs
                        .OrderByDescending(o => {
                            var bb = o.GetBoundingBox(false);
                            return (bb.Max.X - bb.Min.X) * (bb.Max.Y - bb.Min.Y);
                        })
                        .FirstOrDefault();
                    offsetFail++;
                }

                expanded.Add(chosen ?? c);
            }
            else
            {
                expanded.Add(c);  // offset 실패 시 원본
                offsetFail++;
            }
        }
        Print($"[2] 확장 완료 (offset실패={offsetFail}/{valid.Count})");

        // ── 3. Boolean Union ──────────────────────────────────────────────
        //  Rust: clipper2를 이용한 unary_union (AABB 클러스터링 최적화 포함)
        //  C#: Curve.CreateBooleanUnion → 실패 시 Brep 경유 fallback
        Curve[] result = Curve.CreateBooleanUnion(expanded, tol);
        Print($"[3] Curve.CreateBooleanUnion → {result?.Length.ToString() ?? "null"}개");

        if (result == null || result.Length == 0)
        {
            Print("[3] fallback: Brep 경유 시도...");
            result = BrepUnionFallback(expanded, tol);
            Print($"[3] Brep fallback → {result?.Length.ToString() ?? "null"}개");
        }

        if (result == null || result.Length == 0)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning,
                "Boolean Union 실패 — 원본 Curve 반환 (IDWVisualizer에서 직접 처리됨)");
            unionCurves = valid;
            dbg = $"in={valid.Count}, out={valid.Count}, union_fail=true";
            return;
        }

        // ── 4. 면적이 가장 큰 curve 하나만 선택 ─────────────────────────
        Curve largest = null;
        double largestArea = -1;
        foreach (Curve c in result)
        {
            if (c == null) continue;
            AreaMassProperties amp = AreaMassProperties.Compute(c);
            if (amp != null && amp.Area > largestArea)
            {
                largestArea = amp.Area;
                largest     = c;
            }
        }
        Print($"[4] 최대면적 curve 선택: {largestArea:F0}m² (후보={result.Length}개)");

        if (largest == null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "면적 계산 실패 - 첫 번째 curve 반환");
            largest = result[0];
        }

        unionCurves = new List<Curve> { largest };
        dbg = $"in={valid.Count}, offset_fail={offsetFail}, candidates={result.Length}, area={largestArea:F0}m²";
        Print("[5] 완료.");
        }
        catch (Exception ex)
        {
            Print($"[ERR] {ex.GetType().Name}: {ex.Message}\n{ex.StackTrace}");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ex.Message);
        }
    }

    // ─────────────────────────────────────────────────────────────────────
    //  Brep 경유 Boolean Union fallback
    //  Curve.CreateBooleanUnion 실패 시 Brep.CreateBooleanUnion을 거쳐
    //  naked edge를 추출하여 닫힌 Curve로 반환한다.
    // ─────────────────────────────────────────────────────────────────────
    private Curve[] BrepUnionFallback(List<Curve> curves, double tol)
    {
        try
        {
            var breps = new List<Brep>();
            foreach (Curve c in curves)
            {
                Brep[] pb = Brep.CreatePlanarBreps(c, tol);
                if (pb != null) breps.AddRange(pb);
            }
            if (breps.Count == 0) return null;

            Brep[] united = Brep.CreateBooleanUnion(breps, tol);
            if (united == null || united.Length == 0) return null;

            var outCurves = new List<Curve>();
            foreach (Brep b in united)
            {
                if (b == null) continue;
                // naked edges = 외곽선 (shared edges는 제외)
                Curve[] naked = b.DuplicateNakedEdgeCurves(true, false);
                if (naked == null || naked.Length == 0) continue;
                Curve[] joined = Curve.JoinCurves(naked, tol);
                if (joined != null)
                    outCurves.AddRange(joined.Where(c => c != null && c.IsClosed));
            }
            return outCurves.Count > 0 ? outCurves.ToArray() : null;
        }
        catch (Exception ex)
        {
            Print($"[Fallback ERR] {ex.Message}");
            return null;
        }
    }
}
