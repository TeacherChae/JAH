#! python3
# venv: JAH


import pandas as pd
from src.api_parser.data_seoul_api_parser import DataSeoulOpenAPIParser

api_key = "69785956756272693534507159576d"
parser = DataSeoulOpenAPIParser(api_key)
avg_income_df = parser.to_dataframe_full("VwsmAdstrdNcmCnsmpW")
# print(avg_income_df.columns)
# avg_income_monthly = avg_income_df.groupby('ADSTRD_CD')['MT_AVRG_INCOME_AMT'].mean().reset_index()
avg_income_monthly = avg_income_df.groupby('ADSTRD_CD')['MT_AVRG_INCOME_AMT']
print(avg_income_monthly.head())
# shape_code = list(map(lambda x: int(x + '00'), shape_code)) #앞에서 가지고온 모든 서울시 법정동 코드임
# result = []

# def hang(k):
#     h = avg_income_df['행정동코드'][avg_income_df['법정동코드'] == k]
#     return h


# default_value = avg_income_monthly['월_평균_소득_금액'].mean()


# for i in shape_code:
#     k = list(set(hang(i))) #법정동코드 = 행정동1 + 행정동2 + ''''에서 행정동코드만 가지고옴
#     pop = 0
#     cnt = 0
#     for j in k:
#         j = str(j)
#         j = j[:-2] #뒤에 00을 제거하여 average_income['행정동_코드']의 코드양식과 일치시킴
#         ret = avg_income_monthly['월_평균_소득_금액'][avg_income_monthly['행정동_코드'] == int(j)] #현재 칼럼의 타입이 float64이므로 정수형으로 변환시켜야함int(j)
#         if ret.empty :
#             print(1) # 데이터가 없을 때 확인하기 위해 1을 찍어봄
#         else :
#             pop += int(ret)
#             cnt += 1
#     if cnt == 0 : result.append(default_value)
#     else : result.append(pop / cnt)

# print("법정동 코드별 월 평균 소득:", result)
