import requests
import pandas as pd
import xml.etree.ElementTree as ET
import time
from typing import Optional, List, Dict, Any

class VworldOpenAPIParser:
    """
    XML -> pd.DataFrame
    with data.seoul.go.kr OPEN API
    """

    def __init__(self, api_key: str, base_url: str = "https://api.vworld.kr/req/wfs?key="):
        self.api_key = api_key
        self.base_url = base_url

    def _build_url(self, params: dict) -> str:
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        full_url = f"{self.base_url}?{query_string}"
        return full_url

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

    def terrain(self, ymin,xmin,ymax,xmax, typeCol) :
        params = {
            "SERVICE": "WFS",
            "REQUEST": "GetFeature",
            "TYPENAME": typeCol,
            "BBOX": f"{ymin},{xmin},{ymax},{xmax}",
            "VERSION": "1.1.0",
            "MAXFEATURES": "1000",
            "SRSNAME": "EPSG:4326",
            "OUTPUT": "application/json",
            "EXCEPTIONS": "text/xml",
            "KEY": self.api_key
        }

        url = self._build_url(params)
        root = self._fetch_xml_root(url)
        xml = self._xml_to_records(root)
        return xml
    # ----------------- 공개 메서드 -----------------
    def to_dataframe(self, params: dict) -> pd.DataFrame:
        """단일 구간 호출 -> DataFrame"""
        url = self._build_url(params)
        root = self._fetch_xml_root(url)
        records = self._xml_to_records(root)
        return pd.DataFrame(records)

    # def to_dataframe_full(
    #     self,
    #     service_name: str,
    #     page_size: int = 1000,
    #     start: int = 1,
    #     end: Optional[int] = None,
    #     max_rows: Optional[int] = None,
    #     pause_sec: float = 0.0,
    #     verbose: bool = False,
    # ) -> pd.DataFrame:
    #     """
    #     자동 페이지네이션으로 전체(또는 지정량) 수집.

    #     Parameters
    #     ----------
    #     service_name : str
    #         API 서비스명
    #     page_size : int, default 1000
    #         요청당 레코드 수(서울열린데이터는 보통 1000까지 허용)
    #     start : int, default 1
    #         시작 인덱스(1-based)
    #     end : Optional[int]
    #         끝 인덱스(포함). 지정하면 해당 구간까지만 수집
    #     max_rows : Optional[int]
    #         전체 수집 상한(예: 샘플만 뽑고 싶을 때)
    #     pause_sec : float, default 0.0
    #         페이지간 대기(레이트 리밋 회피용)
    #     verbose : bool, default False
    #         진행상황 출력 여부
    #     """
    #     if page_size <= 0:
    #         raise ValueError("page_size는 양의 정수여야 합니다.")

    #     # 1페이지 먼저 호출하여 total_count 파악
    #     first_end = start + page_size - 1 if end is None else min(end, start + page_size - 1)
    #     url = self._build_url(service_name, start, first_end)
    #     root = self._fetch_xml_root(url)

    #     total_count = self._get_list_total_count(root)  # 없을 수도 있음
    #     first_batch = self._xml_to_records(root)
    #     records: List[Dict[str, Any]] = []
    #     records.extend(first_batch)

    #     # 전체 목표량 계산
    #     if end is not None:
    #         target_total = end - start + 1
    #     elif total_count is not None:
    #         target_total = max(total_count - (start - 1), 0)
    #     else:
    #         # total_count가 없다면, 계속 긁되 '빈 페이지' 나오면 종료
    #         target_total = None

    #     if verbose:
    #         if total_count is not None:
    #             print(f"[INFO] list_total_count = {total_count}")
    #         print(f"[INFO] fetched {len(first_batch)} rows (start={start} ~ end={first_end})")

    #     # 다음 페이지부터 루프
    #     fetched = len(first_batch)
    #     next_start = first_end + 1

    #     while True:
    #         # 종료 조건 1: target_total(알고 있는 총량)에 도달
    #         if target_total is not None and fetched >= target_total:
    #             break

    #         # 종료 조건 2: end(명시된 구간 끝)에 도달
    #         if end is not None and next_start > end:
    #             break

    #         next_end = next_start + page_size - 1
    #         if end is not None:
    #             next_end = min(next_end, end)

    #         url = self._build_url(service_name, next_start, next_end)
    #         root = self._fetch_xml_root(url)
    #         batch = self._xml_to_records(root)

    #         if verbose:
    #             print(f"[INFO] fetched {len(batch)} rows (start={next_start} ~ end={next_end})")

    #         # 종료 조건 3: 더 이상 데이터가 안 나옴 (total_count를 못 얻은 경우 유용)
    #         if not batch:
    #             break

    #         records.extend(batch)
    #         fetched += len(batch)

    #         # 종료 조건 4: max_rows 상한
    #         if max_rows is not None and fetched >= max_rows:
    #             if verbose:
    #                 print(f"[INFO] reached max_rows={max_rows}, stop.")
    #             break

    #         # 다음 루프 준비
    #         next_start = next_end + 1

    #         # 레이트 리밋 회피용 대기
    #         if pause_sec > 0:
    #             time.sleep(pause_sec)

    #     # max_rows로 잘라내기
    #     if max_rows is not None and len(records) > max_rows:
    #         records = records[:max_rows]

    #     return pd.DataFrame(records)

api_key = "5C3E2796-9BD1-3BC1-A884-5BD7AE4D360E"
parser = VworldOpenAPIParser(api_key)
params = {
    "SERVICE" : "WFS&",
    "REQUEST" : "GetFeature&",
    "TYPENAME" : "lt_c_uq111&"
    }

url = parser._build_url(params)
res = requests.get(url)
res = ET.fromstring(res.content)
root = parser._xml_to_records(res)
root = pd.DataFrame(root)
print(root)