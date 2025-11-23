#! python3
# venv: JAH
from src.api_parser.data_seoul_api_parser import DataSeoulOpenAPIParser


api_key = "69785956756272693534507159576d"
parser = DataSeoulOpenAPIParser(api_key)

# 1) 전체 긁기 (list_total_count 이용, 페이지별 1000건씩)
avg_income_df = parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW", page_size=1000)

print(avg_income_df.head())
