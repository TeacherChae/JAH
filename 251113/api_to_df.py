from data_seoul_api_parser import DataSeoulOpenAPIParser


api_key = "69785956756272693534507159576d"
parser = DataSeoulOpenAPIParser(api_key)

# 1) 전체 긁기 (list_total_count 이용, 페이지별 1000건씩)
avg_income_df = parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW", page_size=1000, verbose=True)

# 2. 1~5000
# df_1_5000 = parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW", page_size=1000, end=5000)

# 3. sampling
# df_sample = parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW", page_size=1000, max_rows=3000)

# print(len(df_all), len(df_1_5000), len(df_sample))
print(avg_income_df.head())
