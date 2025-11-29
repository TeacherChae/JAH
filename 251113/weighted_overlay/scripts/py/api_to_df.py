# !python
# venv : JAH_PythonCircle
import locale
locale.setlocale(locale.LC_ALL, 'ko_KR')
import pandas as pd
import rhinoscriptsyntax as rs
from System.Net import HttpWebRequest, WebRequest
from System.IO import StreamReader
import json
import clr
import xml.etree.ElementTree as ET

def read(apiurl) : 
    request = WebRequest.Create(apiurl)
    request.Method = "GET"
    response = request.GetResponse()
    stream = response.GetResponseStream()
    reader = StreamReader(stream)
    responseText = reader.ReadToEnd()
    return responseText

def parse_xml_recursive(element):
    """재귀적으로 XML 데이터를 파싱하여 딕셔너리로 반환."""
    data = {}
    for child in element:
        if len(child):  # 하위 태그가 있는 경우
            data[child.tag] = parse_xml_recursive(child)
        else:  # 하위 태그가 없는 경우
            data[child.tag] = child.text
    return data

def parse_xml_response(xml_response):
    """XML 응답을 루트로 시작해 파싱."""
    root = ET.fromstring(xml_response)  # XML 문자열을 ElementTree로 변환
    parsed_data = parse_xml_recursive(root)  # 재귀적으로 파싱
    return parsed_data

url = URL
key = api_key
service = service
area = area

apiurl = f"{url}/{key}/xml/{service}/1/5/{area}"


# print(apiurl)
response = read(apiurl)
# parsed_data = parse_xml_dynamic(response)

# # 결과 출력
# for data in parsed_data:
#     print(data)

parsed_data = parse_xml_response(response)

# 결과 출력
import json
print(json.dumps(parsed_data, ensure_ascii=False, indent=4))
# ROAD_TRAFFIC_STTS 추출
road_traffic_stts = parsed_data['CITYDATA']['ROAD_TRAFFIC_STTS']

# ROAD_TRAFFIC_STTS를 DataFrame으로 변환
road_traffic_stts_df = pd.DataFrame([road_traffic_stts['ROAD_TRAFFIC_STTS']])

name_spd_idx = road_traffic_stts_df[['ROAD_NM','SPD','IDX']]