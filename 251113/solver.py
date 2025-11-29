#! python3
# venv: JAH

from src.api_parser.vworld_api_parser import VworldOpenAPIParser
from src.api_parser.data_seoul_api_parser import DataSeoulOpenAPIParser
from src.gis_util.adstrd_cd_to_legald_cd import get_mapping_df
import pandas as pd

# 1. API 키 설정
vworld_api_key = "2F23FA9B-2FB7-30B4-9335-A9D15732985F"
data_seoul_api_key = "69785956756272693534507159576d"

# 2. Parser 준비
vworld_parser = VworldOpenAPIParser(vworld_api_key)
data_seoul_parser = DataSeoulOpenAPIParser(data_seoul_api_key)

# 3. 데이터 불러오기

# legal district (기준 df)
address1 = "인천 남동구 도림동"
address2 = "경기 남양주시 해밀예당1로 272"

legald_df = vworld_parser.get_legal_district_by_addresses(address1, address2)
legald_df = legald_df[legald_df["area"] > 100]
print("법정동 데이터프레임:")
print(legald_df.head())

# avg_income
avg_income_df = data_seoul_parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW")
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

# 4. legal - avg_income 매핑 준비
file_path = "D:/Keon Chae/Workshop/JAH_PythonCircle/251113/KIKmix.20240201.xlsx"
mapping_df = get_mapping_df(file_path)
print("매핑 데이터프레임:")
print(mapping_df.head())

# 5. mapping_df에 avg_income 붙이기 (adstrd_cd 기준)
mapping_with_income = mapping_df.merge(
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
legald_with_avg_income = legald_df.merge(
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
