#! python3
# venv: JAH

from src.utils.api.vworld_api_parser import VworldOpenAPIParser
from src.utils.api.data_seoul_api_parser import DataSeoulOpenAPIParser
from src.utils.gis.adstrd_cd_to_legald_cd import get_mapping_df
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Optional
import os
import pandas as pd


@dataclass
class URSUSSolver:
    vworld_parser: Optional[VworldOpenAPIParser] = None
    data_seoul_parser: Optional[DataSeoulOpenAPIParser] = None

    # 1. API 키 설정
    def _load_api_keys(self) -> tuple[str, str]:
        load_dotenv()
        vworld_api_key = os.getenv("VWORLD_API_KEY")
        data_seoul_api_key = os.getenv("DATA_SEOUL_API_KEY")

        if not vworld_api_key or not data_seoul_api_key:
            raise ValueError("Missing API keys in .env")

        return vworld_api_key, data_seoul_api_key

    # 2. Parser 준비
    def _set_parser(self):
        vworld_api_key, data_seoul_api_key = self._load_api_keys()
        self.vworld_parser = VworldOpenAPIParser(vworld_api_key)
        self.data_seoul_parser = DataSeoulOpenAPIParser(data_seoul_api_key)

    # 3. 데이터 불러오기
    # legal district (기준 df)
    def _get_legal_district(self, address1: str, address2: str) -> pd.DataFrame:
        if self.vworld_parser is None:
            raise RuntimeError("Parser is not initialized. Call _set_parser() first.")
        legald_df = self.vworld_parser.get_legal_district_by_addresses(address1, address2)
        legald_df = legald_df[legald_df["area"] > 100]
        print("법정동 데이터프레임:")
        print(legald_df.head())
        return legald_df

    # avg_income
    def _get_avg_income(self) -> tuple[float, pd.DataFrame]:
        if self.data_seoul_parser is None:
            raise RuntimeError("Parser is not initialized. Call _set_parser() first.")
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

    # 4. legal - avg_income 매핑 준비
    def _get_mapping_df(self) -> pd.DataFrame:
        file_path = "D:/Keon Chae/Workshop/JAH_PythonCircle/src/sheets/KIKmix.20240201.xlsx"
        mapping_df = get_mapping_df(file_path)
        print("매핑 데이터프레임:")
        print(mapping_df.head())
        return mapping_df

    def run(self):
        self._set_parser()
        legald_df = self._get_legal_district(address1="인천 남동구 도림동", address2="경기 남양주시 해밀예당1로 272")
        mean, avg_income_by_adstrd = self._get_avg_income()
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
    solver.run()




