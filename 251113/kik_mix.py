import openpyxl
import pandas as pd
file_path = "C:\Users\msi\Desktop\KH\JAH\JAH\251113\KIKmix.20240201.xlsx"
df = pd.read_excel(file_path, engine='openpyxl')
df = df[df['시도명'].str.contains('서울특별시')]
df['address'] = df['시도명'] + ' ' + df['시군구명'] + ' ' + df['동리명']
df = df