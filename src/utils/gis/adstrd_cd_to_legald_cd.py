import pandas as pd
import openpyxl

def get_mapping_df(file_path) -> pd.DataFrame:
    """행정동 코드를 법정동 코드로 매핑하는 데이터프레임 반환"""
    df = pd.read_excel(file_path, engine='openpyxl')
    df = df[df["시도명"].str.startswith("서울", na=False)]
    mapping = {"행정동코드": "adstrd_cd", "법정동코드": "legald_cd"}
    df_grouped = df[list(mapping.keys())]
    df_renamed = df_grouped.rename(columns=mapping)
    cols = list(mapping.values())
    df_renamed[cols] = df_renamed[cols].astype(str).apply(lambda col: col.str[:-2])
    return df_renamed

file_path = "D:/Keon Chae/Workshop/JAH_PythonCircle/251113/KIKmix.20240201.xlsx"
mapping_df = get_mapping_df(file_path)
print(mapping_df)
