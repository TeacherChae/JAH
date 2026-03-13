#! python3
# venv: JAH

import json
import time
import pandas as pd
import requests
from pathlib import Path
from typing import Optional
import Rhino.Geometry as rg
from src.utils.gis.gps_to_upm import GPStoUTM

_CACHE_TTL_DAYS = 30


class VworldOpenAPIParser:
    """
    JSON -> pd.DataFrame
    with vworld.kr OPEN API
    """

    def __init__(self, api_key: str, cache_dir: Optional[Path] = None):
        self.api_key   = api_key
        self.cache_dir = cache_dir
        self.wfs_url = "https://api.vworld.kr/req/wfs"
        self.geocoder_url = "https://api.vworld.kr/req/address"
        self.wfs_params = {
            "SERVICE": "WFS",
            "REQUEST": "GetFeature",
            "TYPENAME": "lt_c_ademd_info",
            "BBOX": f"{0},{0},{1},{1}",
            "VERSION": "2.0.0",
            "COUNT": "1000",
            "STARTINDEX": "0",
            "SRSNAME": "EPSG:4326",
            "OUTPUT": "application/json",
            "EXCEPTIONS": "text/xml",
            "KEY": self.api_key,
        }
        self.geocoder_params = {
            "service": "address",
            "request": "getcoord",
            "crs": "EPSG:4326",
            "address": None,
            "format": "json",
            "type": "road",
            "key": self.api_key,
        }

    def get_legal_district_by_addresses(
        self, address1: str, address2: str
    ) -> pd.DataFrame:
        """법정동 경계 DataFrame (TTL 캐시 적용)"""
        cache_path = self.cache_dir / "legald_boundaries.json" if self.cache_dir else None

        if cache_path and self._is_cache_valid(cache_path):
            remaining = _CACHE_TTL_DAYS - (time.time() - cache_path.stat().st_mtime) / 86400
            print(f"[CACHE] legald_boundaries 캐시 사용 (만료까지 {remaining:.1f}일)")
            return self._load_cache(cache_path)

        print("[CACHE] legald_boundaries API 호출 중...")
        df = self._fetch_legal_district(address1, address2)

        if cache_path:
            self._save_cache(df, cache_path)

        return df

    def _fetch_legal_district(self, address1: str, address2: str) -> pd.DataFrame:
        """실제 API 호출 + Geometry 생성"""
        res = []
        data = self._get_full_row_data(address1=address1, address2=address2)
        for datum in data:
            for feature in datum["features"]:
                coords = feature["geometry"]["coordinates"]
                feat_name = feature["properties"]["full_nm"]
                if "서울" in feat_name:
                    points = []
                    for coord in coords[0][0]:
                        gps_to_utm = GPStoUTM()
                        x, y = gps_to_utm.LLtoUTM(coord[1], coord[0])
                        try:
                            pt = rg.Point3d(x, y, 0)
                            points.append(pt)
                        except:
                            ValueError("Coordinate conversion error")
                    try:
                        polyline = rg.Polyline(points)
                        if not polyline.IsClosed:
                            polyline.Add(polyline[0])
                        polyline_curve = rg.PolylineCurve(polyline)
                        amp = rg.AreaMassProperties.Compute(polyline_curve)
                        res.append({
                            "legald_cd": feature["properties"]["emd_cd"],
                            "name":      feat_name,
                            "geometry":  polyline_curve,
                            "area":      amp.Area,
                            "centroid":  amp.Centroid,
                        })
                    except:
                        ValueError("Geometry creation error")
        return pd.DataFrame(res)

    def _is_cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        age_days = (time.time() - path.stat().st_mtime) / 86400
        return age_days < _CACHE_TTL_DAYS

    def _save_cache(self, df: pd.DataFrame, path: Path) -> None:
        """PolylineCurve/Point3d → 좌표 배열로 직렬화하여 저장"""
        records = []
        for _, row in df.iterrows():
            pl = row["geometry"].ToPolyline()
            records.append({
                "legald_cd": row["legald_cd"],
                "name":      row["name"],
                "area":      row["area"],
                "centroid":  [row["centroid"].X, row["centroid"].Y],
                "coords":    [[pt.X, pt.Y] for pt in pl],
            })
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False)
        print(f"[CACHE] legald_boundaries 저장 완료 ({len(records)}건)")

    def _load_cache(self, path: Path) -> pd.DataFrame:
        """좌표 배열 → Rhino Geometry 재생성"""
        with open(str(path), "r", encoding="utf-8") as f:
            records = json.load(f)
        rows = []
        for r in records:
            points = [rg.Point3d(c[0], c[1], 0) for c in r["coords"]]
            pl = rg.Polyline(points)
            if not pl.IsClosed:
                pl.Add(pl[0])
            rows.append({
                "legald_cd": r["legald_cd"],
                "name":      r["name"],
                "geometry":  rg.PolylineCurve(pl),
                "area":      r["area"],
                "centroid":  rg.Point3d(r["centroid"][0], r["centroid"][1], 0),
            })
        return pd.DataFrame(rows)

    def _get_wfs_url(self, params: dict):
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        full_url = f"{self.wfs_url}?{query_string}"
        return full_url

    def _get_geocoder_url(self, params: dict):
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        full_url = f"{self.geocoder_url}?{query_string}"
        return full_url

    def _fetch_json(self, url: str):
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError(f"HTTP Error {response.status_code} for URL: {url}")

        # JSON이 아닐 경우 대비
        try:
            return response.json()
        except ValueError:
            print("===== RAW RESPONSE =====")
            print(response.text[:500])
            raise ValueError("Invalid JSON returned from server")

    def _address_to_coord(self, address: str):
        params = self.geocoder_params.copy()
        params["address"] = address
        url = self._get_geocoder_url(params)
        data = self._fetch_json(url)
        x_coord = data["response"]["result"]["point"]["x"]
        y_coord = data["response"]["result"]["point"]["y"]
        return tuple(map(float, [x_coord, y_coord]))

    def _get_district_boundary_data(self, start_index, count, ymin, xmin, ymax, xmax):
        params = self.wfs_params.copy()
        params["STARTINDEX"] = str(start_index)
        params["COUNT"] = str(count)
        params["BBOX"] = f"{xmin},{ymin},{xmax},{ymax}"
        url = self._get_wfs_url(params)
        data = self._fetch_json(url)
        return data

    def _get_full_row_data(
        self,
        address1: str,
        address2: str,
        batch_size: int = 1000,
        start: int = 0,
        end: Optional[int] = 1000,
        max_rows: Optional[int] = None,
        verbose: bool = False,
    ):
        first_end = (
            start + batch_size - 1 if end is None else min(end, start + batch_size - 1)
        )
        xmin, ymin = self._address_to_coord(address1)
        xmax, ymax = self._address_to_coord(address2)
        first_batch = self._get_district_boundary_data(
            start, batch_size, ymin, xmin, ymax, xmax
        )
        records = []
        records.append(first_batch)

        if verbose:
            print(
                f"[INFO] fetched {len(first_batch)} rows (start={start} ~ end={first_end})"
            )

        # 다음 페이지부터 루프
        fetched = len(first_batch)
        next_start = first_end + 1

        while True:
            # 종료 조건 1: end(명시된 구간 끝)에 도달
            if end is not None and next_start > end:
                break

            next_end = next_start + batch_size - 1
            if end is not None:
                next_end = min(next_end, end)

            batch = self._get_district_boundary_data(
                next_start, batch_size, ymin, xmin, ymax, xmax
            )

            if verbose:
                print(
                    f"[INFO] fetched {len(batch)} rows (start={next_start} ~ end={next_end})"
                )

            # 종료 조건 2: 더 이상 데이터가 안 나옴 (total_count를 못 얻은 경우 유용)
            if not batch:
                break

            records.append(batch)
            fetched += len(batch)

            # 종료 조건 3: max_rows 상한
            if max_rows is not None and fetched >= max_rows:
                if verbose:
                    print(f"[INFO] reached max_rows={max_rows}, stop.")
                break

            # 다음 루프 준비
            next_start = next_end + 1
        return records
