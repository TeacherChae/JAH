#! python3
# venv: JAH

from src.utils.api.vworld_api_parser import VworldOpenAPIParser
from src.utils.api.data_seoul_api_parser import DataSeoulOpenAPIParser
from src.utils.gis.adstrd_cd_to_legald_cd import get_mapping_df
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse, unquote
import os
import pandas as pd


class URSUSSolver:

    def __init__(self):
        vworld_api_key, data_seoul_api_key = self._load_api_keys()
        self.vworld_parser = VworldOpenAPIParser(vworld_api_key)
        self.data_seoul_parser = DataSeoulOpenAPIParser(data_seoul_api_key)

    def _file_uri_to_path(self, raw: str) -> Path:
        if raw.startswith("file:///"):
            p = unquote(urlparse(raw).path)
            if len(p) > 2 and p[0] == "/" and p[2] == ":":
                p = p[1:]
            return Path(p)
        return Path(raw)


    def _load_api_keys(self) -> tuple[str, str]:
        """
        API 키 불러오기
        """
        script_path = self._file_uri_to_path(__file__)
        load_dotenv(script_path.parent / ".env")
        vworld_api_key = os.getenv("VWORLD_API_KEY")
        data_seoul_api_key = os.getenv("DATA_SEOUL_API_KEY")
        if not vworld_api_key or not data_seoul_api_key:
            raise ValueError("Missing API keys in .env")

        return vworld_api_key, data_seoul_api_key

    def _get_legal_district_df(self, address1: str, address2: str) -> pd.DataFrame:
        """
        법정동 df

        "legald_cd": 법정동 코드,
        "name": 법정동 명,
        "geometry": 법정동 경계 geometry,
        "area": 법정동 면적,
        "centroid": 법정동 중점,
        """
        legald_df = self.vworld_parser.get_legal_district_by_addresses(address1, address2)
        legald_df = legald_df[legald_df["area"] > 100]
        print("법정동 데이터프레임:")
        print(legald_df.head())
        return legald_df

    # avg_income
    def _get_avg_income_df(self) -> tuple[float, pd.DataFrame]:
        """
        행정동 기준 월 평균 소득 df

        "adstrd_cd": 행정동 코드,
        "mt_avrg_income": 월 평균 소득,
        """
        avg_income_df = self.data_seoul_parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW")
        print("평균 소득 데이터프레임:")
        avg_income_df.columns = (
            avg_income_df.columns.str.strip().str.lower()
        )
        print(avg_income_df.head())
        avg_income_df["mt_avrg_income_amt"] = pd.to_numeric(
            avg_income_df["mt_avrg_income_amt"],
            errors="coerce"
        )
        mean = avg_income_df["mt_avrg_income_amt"].mean()
        avg_income_by_adstrd = avg_income_df.groupby("adstrd_cd")["mt_avrg_income_amt"].mean().reset_index()
        avg_income_by_adstrd["mt_avrg_income_amt"].fillna(mean, inplace=True)
        return mean, avg_income_by_adstrd

    def _get_mapping_df(self) -> pd.DataFrame:
        """
        행정동 df <-> 법정동 df 매칭
        """
        file_path = "D:/Keon Chae/Workshop/JAH_PythonCircle/src/sheets/KIKmix.20240201.xlsx"
        mapping_df = get_mapping_df(file_path)
        print("매핑 데이터프레임:")
        print(mapping_df.head())
        return mapping_df

    def run(self):
        """
        solver.run()

        TODO: to be continued
        """
        legald_df = self._get_legal_district_df(address1="인천 남동구 도림동", address2="경기 남양주시 해밀예당1로 272")
        mean, avg_income_by_adstrd = self._get_avg_income_df()
        mapping_df = self._get_mapping_df()
        # # 5. mapping_df에 avg_income 붙이기 (adstrd_cd 기준)
        mapping_with_income: pd.DataFrame = mapping_df.merge(
            avg_income_by_adstrd,
            on="adstrd_cd",
            how="left",
        )
        print("매핑된 평균 소득 데이터프레임:")
        print(mapping_with_income.head())

        # 6. legald_cd 기준으로 평균 내기
        avg_income_by_legald = (
            mapping_with_income
            .groupby("legald_cd", as_index=False)["mt_avrg_income_amt"]
            .mean()
        )
        print("법정동 코드별 평균 소득 데이터프레임:")
        print(avg_income_by_legald.head())

        # 7. legal df에 avg_income 붙이기
        legald_with_avg_income: pd.DataFrame = legald_df.merge(
            avg_income_by_legald,
            on="legald_cd",
            how="left",
        )
        legald_with_avg_income["mt_avrg_income_amt"].fillna(mean, inplace=True)

        print("법정동 데이터프레임에 평균 소득 추가:")
        print(legald_with_avg_income)

        # 8. 결과 활용
        geometries = legald_with_avg_income["geometry"].to_list()
        centroids = legald_with_avg_income["centroid"].to_list()
        avg_incomes = legald_with_avg_income["mt_avrg_income_amt"].to_list()

        return geometries, centroids, avg_incomes

if __name__ == "__main__":
    solver = URSUSSolver()
    geometries, centroids, avg_incomes = solver.run()




