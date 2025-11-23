# venv: JAH

import logging
import requests
from typing import Optional
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
from src.gis_util.gps_to_upm import GPStoUTM
from src.io_format.admin_district import AdministrativeDistrict


class VworldOpenAPIParser:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.wfs_url = "https://api.vworld.kr/req/wfs?key="
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
            "KEY": self.api_key
        }
        self.geocoder_params = {
            "service" : "address",
            "request" : "getcoord",
            "crs" : "EPSG:4326",
            "address": None,
            "format" : "json",
            "type" : "road",
            "key" : self.api_key
        }

    def admin_district_by_addresses(self, address1: str, address2: str)-> list[AdministrativeDistrict]:
        res = []
        data = self._get_full_row_data(address1=address1, address2=address2)
        for datum in data:
            for feature in datum["features"]:
                coords = feature["geometry"]["coordinates"]
                feat_name = feature["properties"]["full_nm"]
                if "서울"in feat_name:
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
                        if amp.Area <= 100:
                        admin_district = AdministrativeDistrict(
                            name=feat_name,
                            code=feature["properties"]["emd_cd"],
                            geometry=polyline_curve,
                            area=amp.Area,
                            centroid=amp.Centroid
                        )
                        res.append(admin_district)
                    except:
                        ValueError("Geometry creation error")
        return res

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
        x_coord = data['response']['result']['point']['x']
        y_coord = data['response']['result']['point']['y']
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
        # 1페이지 먼저 호출하여 total_count 파악
        first_end = start + batch_size - 1 if end is None else min(end, start + batch_size - 1)
        xmin, ymin = self._address_to_coord(address1)
        xmax, ymax = self._address_to_coord(address2)
        first_batch = self._get_district_boundary_data(start, batch_size, ymin, xmin, ymax, xmax)
        records = []
        records.append(first_batch)

        if verbose:
            print(f"[INFO] fetched {len(first_batch)} rows (start={start} ~ end={first_end})")

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

            batch = self._get_district_boundary_data(next_start, batch_size, ymin, xmin, ymax, xmax)

            if verbose:
                print(f"[INFO] fetched {len(batch)} rows (start={next_start} ~ end={next_end})")

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
