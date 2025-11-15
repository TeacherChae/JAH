import requests
import pandas as pd
import xml.etree.ElementTree as ET
import time
from typing import Optional, List, Dict, Any

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
        """
        extracting total row counts
        """
        node = root.find(".//list_total_count")
        if node is None or (node.text is None):
            return None
        txt = node.text.strip()
        return int(txt) if txt.isdigit() else None

    def to_dataframe(self, service_name: str, start: int = 1, end: int = 100) -> pd.DataFrame:
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
        collecting data with auto-pagination

        Parameters
        ----------
        service_name : API service title
        page_size : record count
        pause_sec : avoid late-limit
        verbose : check logs
        """
        if page_size <= 0:
            raise ValueError("page_size must be a natural number.")

        first_end = start + page_size - 1 if end is None else min(end, start + page_size - 1)
        url = self._build_url(service_name, start, first_end)
        root = self._fetch_xml_root(url)

        # extract total count
        total_count = self._get_list_total_count(root)
        first_batch = self._xml_to_records(root)
        records: List[Dict[str, Any]] = []
        records.extend(first_batch)

        if end is not None:
            target_total = end - start + 1
        elif total_count is not None:
            target_total = max(total_count - (start - 1), 0)
        else:
            target_total = None

        if verbose:
            if total_count is not None:
                print(f"[INFO] list_total_count = {total_count}")
            print(f"[INFO] fetched {len(first_batch)} rows (start={start} ~ end={first_end})")

        # loop start
        fetched = len(first_batch)
        next_start = first_end + 1

        while True:
            # 1: target_total
            if target_total is not None and fetched >= target_total:
                break

            # 2. end
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

            # 3. no more data (if not total_count)
            if not batch:
                break

            records.extend(batch)
            fetched += len(batch)

            # 4. max_rows limit
            if max_rows is not None and fetched >= max_rows:
                if verbose:
                    print(f"[INFO] reached max_rows={max_rows}, stop.")
                break

            next_start = next_end + 1

            # avoiding late limit
            if pause_sec > 0:
                time.sleep(pause_sec)

        # slicing by max_rows
        if max_rows is not None and len(records) > max_rows:
            records = records[:max_rows]

        return pd.DataFrame(records)


api_key = "707372594162726936364c44614e78"
parser = SeoulOpenAPIParser(api_key)

# 1. whole
df_all = parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW", page_size=1000, verbose=True)
print(df_all)

# 2. 1~5000
# df_1_5000 = parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW", page_size=1000, end=5000)

# 3. sampling
# df_sample = parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW", page_size=1000, max_rows=3000)

# print(df_all.head())