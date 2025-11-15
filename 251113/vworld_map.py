import pandas as pd
import json
from math import sin, cos, tan, pi, sqrt
import re
from xml.etree import ElementTree as ET
from typing import Optional, List, Dict, Any
import requests

RADIANS_PER_DEGREE = pi/180.0
DEGREES_PER_RADIAN = 180.0/pi

WGS84_A =  6378137.0
WGS84_B =  6356752.31424518
WGS84_F =  0.0033528107
WGS84_E =  0.0818191908
WGS84_EP = 0.0820944379

UTM_K0 =   0.9996
UTM_FE =   500000.0
UTM_FN_N = 0.0
UTM_FN_S = 10000000.0
UTM_E2 =   (WGS84_E*WGS84_E)
UTM_E4 =   (UTM_E2*UTM_E2)
UTM_E6 =   (UTM_E4*UTM_E2)
UTM_EP2 =  (UTM_E2/(1-UTM_E2))

class GPStoUTM(object):
    def __init__(self, **kwargs):
        pass

    def UTM(self, lat, lon):
        '''
        Gets the UTM coordinate without the letter and number.
        '''
        self.m0 = (1 - UTM_E2/4 - 3*UTM_E4/64 - 5*UTM_E6/256)
        self.m1 = -(3*UTM_E2/8 + 3*UTM_E4/32 + 45*UTM_E6/1024)
        self.m2 = (15*UTM_E4/256 + 45*UTM_E6/1024)
        self.m3 = -(35*UTM_E6/3072)

        if lon > 0:
            self.cm = int(lon) - (int(lon) % 6) + 3
        else:
            self.cm = int(lon) - (int(lon) % 6) - 3

        self.rlat = lat * RADIANS_PER_DEGREE
        self.rlon = lon * RADIANS_PER_DEGREE
        self.rlon0 = self.cm * RADIANS_PER_DEGREE

        self.slat = sin(self.rlat)
        self.clat = cos(self.rlat)
        self.tlat = tan(self.rlat)

        if lat > 0:
            self.fn = UTM_FN_N
        else:
            self.fn = UTM_FN_S

        self.T = self.tlat*self.tlat
        self.C = UTM_EP2 * self.clat * self.clat
        self.A = (self.rlon - self.rlon0) * self.clat
        self.M = WGS84_A * (self.m0*self.rlat + self.m1*sin(2*self.rlat) + \
            self.m2*sin(4*self.rlat) + self.m3*sin(6*self.rlat))
        self.V = WGS84_A / sqrt(1 - UTM_E2 * self.slat * self.slat)

        self.x = UTM_FE + UTM_K0 * self.V * (self.A + (1-self.T+self.C)\
            *pow(self.A, 3)/6 +(5-18*self.T+self.T*self.T+72*self.C-58*UTM_EP2)\
            *pow(self.A, 5)/120)

        self.y = self.fn + UTM_K0 * (self.M + self.V * self.tlat * \
            (self.A*self.A/2 + (5-self.T+9*self.C+4*self.C*self.C)* \
            pow(self.A, 4)/24 + ((61-58*self.T+self.T*self.T+600*self.C-\
            330*UTM_EP2) * pow(self.A, 6)/720)))

        return (self.x, self.y)

    def UTMLetterDesignator(self, Lat):
        '''
        Gets the UTM letter only.
        '''
        self.LetterDesignator = 'Z'
        if ((84 >= Lat) and (Lat >= 72)):
            self.LetterDesignator = 'X'
        elif ((72 > Lat) and (Lat >= 64)):
            self.LetterDesignator = 'W'
        elif ((64 > Lat) and (Lat >= 56)):
            self.LetterDesignator = 'V'
        elif ((56 > Lat) and (Lat >= 48)):
            self.LetterDesignator = 'U'
        elif ((48 > Lat) and (Lat >= 40)):
            self.LetterDesignator = 'T'
        elif ((40 > Lat) and (Lat >= 32)):
            self.LetterDesignator = 'S'
        elif ((32 > Lat) and (Lat >= 24)):
            self.LetterDesignator = 'R'
        elif ((24 > Lat) and (Lat >= 16)):
            self.LetterDesignator = 'Q'
        elif ((16 > Lat) and (Lat >= 8)):
            self.LetterDesignator = 'P'
        elif (( 8 > Lat) and (Lat >= 0)):
            self.LetterDesignator = 'N'
        elif (( 0 > Lat) and (Lat >= -8)):
            self.LetterDesignator = 'M'
        elif ((-8 > Lat) and (Lat >= -16)):
            self.LetterDesignator = 'L'
        elif ((-16 > Lat) and (Lat >= -24)):
            self.LetterDesignator = 'K'
        elif ((-24 > Lat) and (Lat >= -32)):
            self.LetterDesignator = 'J'
        elif ((-32 > Lat) and (Lat >= -40)):
            self.LetterDesignator = 'H'
        elif ((-40 > Lat) and (Lat >= -48)):
            self.LetterDesignator = 'G'
        elif ((-48 > Lat) and (Lat >= -56)):
            self.LetterDesignator = 'F'
        elif ((-56 > Lat) and (Lat >= -64)):
            self.LetterDesignator = 'E'
        elif ((-64 > Lat) and (Lat >= -72)):
            self.LetterDesignator = 'D'
        elif ((-72 > Lat) and (Lat >= -80)):
            self.LetterDesignator = 'C'
        return self.LetterDesignator

    def LLtoUTM(self, Lat, Long):
        '''
        Gets the UTM coordinate with the letter and number as inputs also.
        '''
        self.a = WGS84_A;
        self.eccSquared = UTM_E2;
        self.k0 = UTM_K0;

        self.LongTemp = (Long+180)-int((Long+180)/360)*360-180

        self.LatRad = Lat * RADIANS_PER_DEGREE
        self.LongRad = self.LongTemp * RADIANS_PER_DEGREE

        self.ZoneNumber = int((self.LongTemp+180)/6) + 1

        self.LongOrigin = (self.ZoneNumber-1)*6 - 180 + 3
        self.LongOriginRad = self.LongOrigin * RADIANS_PER_DEGREE

        self.eccPrimeSquared = (self.eccSquared)/(1-self.eccSquared);

        self.N = self.a/sqrt(1-self.eccSquared*sin(self.LatRad)*\
            sin(self.LatRad));
        self.T = tan(self.LatRad)*tan(self.LatRad);
        self.C = self.eccPrimeSquared*cos(self.LatRad)*cos(self.LatRad);
        self.A = cos(self.LatRad)*(self.LongRad-self.LongOriginRad);

        self.M = self.a*((1 - self.eccSquared/4 -\
            3*self.eccSquared*self.eccSquared/64 -\
            5*self.eccSquared*self.eccSquared*self.eccSquared/256) * \
            self.LatRad - (3*self.eccSquared/8 + 3*self.eccSquared*\
            self.eccSquared/32 +45*self.eccSquared*self.eccSquared*\
            self.eccSquared/1024)*sin(2*self.LatRad) + (15*self.eccSquared*\
            self.eccSquared/256 + 45*self.eccSquared*self.eccSquared*\
            self.eccSquared/1024)*sin(4*self.LatRad) - (35*self.eccSquared*\
            self.eccSquared*self.eccSquared/3072)*sin(6*self.LatRad))

        self.UTMEasting = float(self.k0*self.N*(self.A+(1-self.T+self.C)*\
            self.A**3/6 + (5-18*self.T+self.T*self.T+72*self.C-58*\
            self.eccPrimeSquared)*self.A**4/120) + 500000.0)

        self.UTMNorthing = float(self.k0*(self.M+self.N*tan(self.LatRad)\
            *(self.A**2/2+(5-self.T+9*self.C+4*self.C**2)*self.A**4/24 + (61-58\
            *self.T+self.T**2+600*self.C-330*self.eccPrimeSquared)\
            *self.A**6/720)))

        if (Lat < 0):
            self.UTMNorthing += 10000000.0

        return (self.UTMEasting, self.UTMNorthing)

    def UTMtoLL(self, UTMNorthing, UTMEasting, UTMNumber, UTMLetter):
        '''
        Gets the latitude and longitude with the UTM letter and number.
        '''
        self.ZoneNumber = int(UTMNumber)
        self.ZoneLetter = UTMLetter

        self.k0 = UTM_K0
        self.a = WGS84_A
        self.eccSquared = UTM_E2
        self.e1 = (1-sqrt(1-self.eccSquared))/(1+sqrt(1-self.eccSquared))

        self.x = UTMEasting - 500000.0
        self.y = UTMNorthing

        if self.ZoneLetter < 'N':
            self.y -= 10000000.0

        self.LongOrigin = (self.ZoneNumber - 1)*6 - 180 + 3
        self.eccPrimeSquared = (self.eccSquared)/(1-self.eccSquared)

        self.M = self.y/self.k0;
        self.mu = self.M/(self.a*(1-self.eccSquared/4-3*self.eccSquared**2/64\
            -5*self.eccSquared**3/256))

        self.phi1Rad = self.mu + ((3*self.e1/2-27*self.e1**3/32)*sin(2*self.mu)\
            + (21*self.e1**2/16-55*self.e1**4/32)*sin(4*self.mu)\
            + (151*self.e1**3/96)*sin(6*self.mu))

        self.N1 = self.a/sqrt(1-self.eccSquared*sin(self.phi1Rad)**2)
        self.T1 = tan(self.phi1Rad)**2
        self.C1 = self.eccPrimeSquared*cos(self.phi1Rad)**2
        self.R1 = self.a*(1-self.eccSquared)/pow(1-self.eccSquared*sin(self.phi1Rad)**2, 1.5)
        self.D = self.x/(self.N1*self.k0)

        self.Lat = self.phi1Rad - ((self.N1*tan(self.phi1Rad)/self.R1)\
            *(self.D**2/2-(5+3*self.T1+10*self.C1-4*self.C1**2-9\
            *self.eccPrimeSquared)*self.D**4/24+(61+90*self.T1+298*self.C1\
            +45*self.T1**2-252*self.eccPrimeSquared-3*self.C1**2)\
            *self.D**6/720))

        self.Lat = self.Lat * DEGREES_PER_RADIAN

        self.Long = ((self.D-(1+2*self.T1+self.C1)*self.D**3/6+(5-2*self.C1\
            +28*self.T1-3*self.C1**2+8*self.eccPrimeSquared+24*self.T1**2)\
            *self.D**5/120)/cos(self.phi1Rad))

        self.Long = self.LongOrigin + self.Long * DEGREES_PER_RADIAN

        return (self.Lat, self.Long)

gps = GPStoUTM()


class SeoulOpenAPIParser:
    """
    XML -> pd.DataFrame
    with data.seoul.go.kr OPEN API
    """

    def __init__(self, api_key: str, base_url: str = "http://openapi.seoul.go.kr:8088"):
        self.api_key = api_key
        self.base_url = base_url

    def _build_url(self, service_name: str, start: int, end: int) -> str:
        return f"{self.base_url}/{self.api_key}/xml/{service_name}/{start}/{end}/"

    def _fetch_xml_root(self, url: str) -> ET.Element:
        """
        url -> XML
        """
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        # API 응답 내 에러 처리 (RESULT 코드 확인)
        result = root.find(".//RESULT")
        if result is not None:
            code = (result.findtext("CODE") or "").strip()
            msg  = (result.findtext("MESSAGE") or "").strip()
            # INFO-000 = 정상, 그 외에도 "정상 처리되었습니다" 메시지면 통과
            if code and code != "INFO-000" and "정상" not in msg:
                raise RuntimeError(f"API 오류: {code} - {msg}")
        return root

    def _xml_to_records(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        <row> -> list[dict[col, val]]
        """
        records = []
        for row in root.iter("row"):
            rec = {child.tag: (child.text or "").strip() for child in row}
            records.append(rec)
        return records

    def _get_list_total_count(self, root: ET.Element) -> Optional[int]:
        """응답 트리 어딘가의 <list_total_count> 추출 (없으면 None)"""
        node = root.find(".//list_total_count")
        if node is None or (node.text is None):
            return None
        txt = node.text.strip()
        return int(txt) if txt.isdigit() else None

    # ----------------- 공개 메서드 -----------------
    def to_dataframe(self, service_name: str, start: int = 1, end: int = 100) -> pd.DataFrame:
        """단일 구간 호출 -> DataFrame"""
        url = self._build_url(service_name, start, end)
        root = self._fetch_xml_root(url)
        records = self._xml_to_records(root)
        return pd.DataFrame(records)

    def to_dataframe_full(
        self,
        service_name: str,
        page_size: int = 1000,
        start: int = 1,
        end: Optional[int] = None,
        max_rows: Optional[int] = None,
        pause_sec: float = 0.0,
        verbose: bool = False,
    ) -> pd.DataFrame:
        """
        자동 페이지네이션으로 전체(또는 지정량) 수집.

        Parameters
        ----------
        service_name : str
            API 서비스명
        page_size : int, default 1000
            요청당 레코드 수(서울열린데이터는 보통 1000까지 허용)
        start : int, default 1
            시작 인덱스(1-based)
        end : Optional[int]
            끝 인덱스(포함). 지정하면 해당 구간까지만 수집
        max_rows : Optional[int]
            전체 수집 상한(예: 샘플만 뽑고 싶을 때)
        pause_sec : float, default 0.0
            페이지간 대기(레이트 리밋 회피용)
        verbose : bool, default False
            진행상황 출력 여부
        """
        if page_size <= 0:
            raise ValueError("page_size는 양의 정수여야 합니다.")

        # 1페이지 먼저 호출하여 total_count 파악
        first_end = start + page_size - 1 if end is None else min(end, start + page_size - 1)
        url = self._build_url(service_name, start, first_end)
        root = self._fetch_xml_root(url)

        total_count = self._get_list_total_count(root)  # 없을 수도 있음
        first_batch = self._xml_to_records(root)
        records: List[Dict[str, Any]] = []
        records.extend(first_batch)

        # 전체 목표량 계산
        if end is not None:
            target_total = end - start + 1
        elif total_count is not None:
            target_total = max(total_count - (start - 1), 0)
        else:
            # total_count가 없다면, 계속 긁되 '빈 페이지' 나오면 종료
            target_total = None

        if verbose:
            if total_count is not None:
                print(f"[INFO] list_total_count = {total_count}")
            print(f"[INFO] fetched {len(first_batch)} rows (start={start} ~ end={first_end})")

        # 다음 페이지부터 루프
        fetched = len(first_batch)
        next_start = first_end + 1

        while True:
            # 종료 조건 1: target_total(알고 있는 총량)에 도달
            if target_total is not None and fetched >= target_total:
                break

            # 종료 조건 2: end(명시된 구간 끝)에 도달
            if end is not None and next_start > end:
                break

            next_end = next_start + page_size - 1
            if end is not None:
                next_end = min(next_end, end)

            url = self._build_url(service_name, next_start, next_end)
            root = self._fetch_xml_root(url)
            batch = self._xml_to_records(root)

            if verbose:
                print(f"[INFO] fetched {len(batch)} rows (start={next_start} ~ end={next_end})")

            # 종료 조건 3: 더 이상 데이터가 안 나옴 (total_count를 못 얻은 경우 유용)
            if not batch:
                break

            records.extend(batch)
            fetched += len(batch)

            # 종료 조건 4: max_rows 상한
            if max_rows is not None and fetched >= max_rows:
                if verbose:
                    print(f"[INFO] reached max_rows={max_rows}, stop.")
                break

            # 다음 루프 준비
            next_start = next_end + 1

            # 레이트 리밋 회피용 대기
            if pause_sec > 0:
                time.sleep(pause_sec)

        # max_rows로 잘라내기
        if max_rows is not None and len(records) > max_rows:
            records = records[:max_rows]

        return pd.DataFrame(records)


def read(apiurl) :
    request = WebRequest.Create(apiurl)
    request.Method = "GET"
    response = request.GetResponse()
    stream = response.GetResponseStream()
    reader = StreamReader(stream)
    responseText = reader.ReadToEnd()
    return json.loads(responseText)

def terrain(ymin,xmin,ymax,xmax, typeCol, vworld_key) :
    params = {
        "SERVICE": "WFS",
        "REQUEST": "GetFeature",
        "TYPENAME": typeCol,
        "BBOX": "{0},{1},{2},{3}".format(ymin, xmin, ymax, xmax),
        "VERSION": "1.1.0",
        "MAXFEATURES": "1000",
        "SRSNAME": "EPSG:4326",
        "OUTPUT": "application/json",
        "EXCEPTIONS": "text/xml",
        "KEY": vworld_key
    }

    apiurl = "https://api.vworld.kr/req/wfs"

    # params 딕셔너리를 URL 쿼리 스트링으로 변환
    query_string = "&".join(["{0}={1}".format(key, value) for key, value in params.items()])
    full_url = "{0}?{1}".format(apiurl,query_string)
    data = read(full_url)
    return data


def AddressToCoord(input_address, vworld_key):
    apiurl = "https://api.vworld.kr/req/address?service=address&request=getcoord&crs=EPSG:4326&address={0}&format=json&type=road&key={1}".format(input_address, vworld_key)
    request = WebRequest.Create(apiurl)
    request.Method = "GET"
    response = request.GetResponse()
    stream = response.GetResponseStream()
    reader = StreamReader(stream)
    responseText = reader.ReadToEnd()
    response_data = json.loads(responseText)
    x_coord = response_data['response']['result']['point']['x']
    y_coord = response_data['response']['result']['point']['y']
    return float(x_coord), float(y_coord)

vworld_key = vworld_key
info = {}
select_type = []
select_type.append(typeCol)
dong_geom = []
dong_name = []
dong_code = []
nodata = []
nodataid = []



def remove_numbers(string):
    return re.sub(r'\d+', '', string)


if Run :
    xmin, ymin = AddressToCoord(address1, vworld_key)
    xmax, ymax = AddressToCoord(address2, vworld_key)
    if(ymin > ymax) : ymin, ymax = ymax, ymin
    if(xmin > xmax) : xmin, xmax = xmax, xmin
    data = terrain(ymin, xmin, ymax, xmax, select_type[0], vworld_key)
    try:
        info = data
        features = info["features"]
        for feature in features :
            coords = feature['geometry']['coordinates']
            feat_name = feature['properties']['full_nm']
            print(feature)
            if "서울" in feat_name :
                points = []
                for coord in coords[0][0] :
                    try:
                        x, y = gps.LLtoUTM(coord[1], coord[0])
                        pt = rg.Point3d(x, y, 0)
                        points.append(pt)
                    except: continue
                try :
                    polyline = rs.AddPolyline(points)
                    dong_geom.append(polyline)
                    dong_name.append(feat_name)
                    dong_code.append(feature['properties']['emd_cd'])
                except : pass
    except : pass

shape = dong_geom
shape_name = dong_name
shape_code = dong_code
