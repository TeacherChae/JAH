import pandas as pd

import os

dir_path = os.getcwd()

path = os.path.join(dir_path, "2024_11.xlsx")
data_frame = pd.read_excel(path)
path = os.path.join(dir_path, "2024_11.xlsx")
data_frame = pd.read_excel(path)
print("이 데이터는 2024년 11월에 신축된 건물에 대한 데이터입니다.")
print(data_frame.head())
print(f"총 {len(data_frame)}줄의 데이터입니다.")
print("아래의 column들을 가지고 있습니다.")
print(data_frame.columns)


# 데이터는 Column
all_data = []
for i, row in data_frame.iterrows():
    if (
        i == 10
    ):  # TODO 이 if - break 는 data가 너무 많아서 테스트를 빠르게 하기 위해 작성했습니다.
        # 데이터를 앞에서부터 10개만 보도록 제한합니다. 과제를 어느정도 구현한 후에는 지운 후에 프로그램을 실행해주세요.
        break

    row_dict = row.to_dict()
    print(row_dict)

    # dict는 get을 통해서 값을 가져오거나 []를 통해서 값을 가져올 수 있습니다.
    # get을 사용하면 값이 없을 때 None을 반환합니다.
    # []를 사용하면 값이 없을 때 KeyError가 발생합니다.

    pnu = row.get("PNU")
    lot_area = row.get("PLOT_DIMS")
    build_area = row.get("BULD_AREA")
    gfa = row.get("GRFA")
    building_use = row.get("BULD_MUSES_NM")
    building_structure = row.get("BULD_STRU_NM")

    building_info = {
        "pnu": pnu,
        "lot_area": lot_area,
    }

    all_data.append(building_info)

print(all_data)

# task : 1. 서울의 pnu는 11부터 시작합니다. all data 중에서 11 로 시작하는 pnu를 가진 데이터만 출력해보세요

# task : 2. all_data에 있는 데이터 중에서 lot_area가 1000 이상인 데이터만 출력해보세요

# task : 3. 서울에 새롭게 지어진 건물들의 개수, 평균 lot_area, 평균 build_area, 평균 gfa를 출력해보세요
