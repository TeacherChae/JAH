# venv: JAH

import requests
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
from src.gis_util.gps_to_upm import GPStoUTM


class VworldOpenAPIParser:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.wfs_url = "https://api.vworld.kr/req/wfs?key="
        self.address_url = "https://api.vworld.kr/req/address"

    def _get_wfs_url(self, params: dict):
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        full_url = f"{self.wfs_url}?{query_string}"
        return full_url

    def _get_address_url(self, params: dict):
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        full_url = f"{self.address_url}?{query_string}"
        return full_url

    def _fetch_json(self, url: str):
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def _address_to_coord(self, address: str):
        params = {
            "service" : "address",
            "request" : "getcoord",
            "crs" : "EPSG:4326",
            "address": address,
            "format" : "json",
            "type" : "road",
            "key" : self.api_key
        }
        url = self._get_address_url(params)
        data = self._fetch_json(url)
        x_coord = data['response']['result']['point']['x']
        y_coord = data['response']['result']['point']['y']
        return tuple(map(float, [x_coord, y_coord]))

    def _get_district_boundary_data(self, ymin,xmin,ymax,xmax):
        params = {
            "SERVICE": "WFS",
            "REQUEST": "GetFeature",
            "TYPENAME": "lt_c_uq111&",
            "BBOX": f"{ymin},{xmin},{ymax},{xmax}",
            "VERSION": "1.1.0",
            "MAXFEATURES": "1000",
            "SRSNAME": "EPSG:4326",
            "OUTPUT": "application/json",
            "EXCEPTIONS": "text/xml",
            "KEY": self.api_key
        }
        url = self._get_wfs_url(params)
        data = self._fetch_json(url)
        return data
    
    def terrain_by_addresses(self, address1: str, address2: str):
        geom = []
        name = []
        code = []
        xmin, ymin = self._address_to_coord(address1)
        xmax, ymax = self._address_to_coord(address2)
        if(ymin > ymax):
            ymin, ymax = ymax, ymin
        if(xmin > xmax):
            xmin, xmax = xmax, xmin
        data = self._get_district_boundary_data(ymin, xmin, ymax, xmax)
        # print(data.keys())
        print(len(data['features']))
        # print(len(data["feature"]))
        for feature in data["features"]:
            print(feature['coordinates'])
            coords = feature["geometry"]["coordinates"]
            # print(feature.keys())
            feat_name = feature["properties"]["sido_name"]
            if "서울"in feat_name:
                points = []
                for coord in coords[0][0]:
                    try:
                        x, y = GPStoUTM.LLtoUTM(coord[1], coord[0])
                        # print(x,y)
                        pt = rg.Point3d(x, y, 0)
                        points.append(pt)
                    except:
                        continue
                try:
                    polyline = rs.AddPolyline(points)
                    geom.append(polyline)
                    name.append(feat_name)
                    code.append(feature["properties"]["emd_cd"])
                except:
                    pass
            return geom, name, code