#! python3
# venv: JAH


from src.api_parser.vworld_api_parser import VworldOpenAPIParser

api_key = "2F23FA9B-2FB7-30B4-9335-A9D15732985F"
address1 = "인천 남동구 도림동"
address2 = "경기 남양주시 해밀예당1로 272"

parser = VworldOpenAPIParser(api_key)
geom, name, code = parser.terrain_by_addresses(address1, address2)
# print(geom)
# print(name)