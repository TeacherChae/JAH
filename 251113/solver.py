import pandas as pd
from collections import defaultdict

# 데이터 로드
월평균소득 = pd.read_csv('D:/Keon Chae/Programming Languages/Python/referred_files/서울시 상권분석서비스(소득소비-행정동).csv', encoding="euckr")
average_income = 월평균소득.groupby('행정동_코드')['월_평균_소득_금액'].mean().reset_index()

# 앞에서 가지고 온 모든 서울시 법정동 코드
shape_code = list(map(lambda x: int(x + '00'), shape_code))
result = []

def hang(k):
    """법정동에 해당하는 행정동코드 리스트 반환"""
    h = df['행정동코드'][df['법정동코드'] == k]
    return h

# 기본값 (평균 소득)
default_value = average_income['월_평균_소득_금액'].mean()

for i in shape_code:
    k = list(set(hang(i)))  # 법정동 코드에 해당하는 행정동 코드 리스트
    pop = 0  # 현재 법정동의 평균 소득 초기화
    count = 0  # 유효한 행정동 데이터의 개수
    for j in k:
        j = str(j)[:-2]  # 뒤의 "00" 제거
        j = int(j)  # 정수형으로 변환

        # 행정동 코드에 해당하는 소득값 가져오기
        ret = average_income['월_평균_소득_금액'][average_income['행정동_코드'] == j]

        if ret.empty:
            print(f"행정동 코드 {j}에 해당하는 데이터가 없습니다.")
            continue
        else:
            pop += ret.values[0]  # 소득값 합산
            count += 1  # 유효한 데이터 카운트 증가
    
    # 평균 계산 (유효한 데이터가 있을 경우만)
    if count > 0:
        pop /= count
    else:
        pop = default_value  # 데이터가 없는 경우 기본값 사용
    
    result.append(pop)

print("법정동 코드별 월 평균 소득:", result)