#! python3
# venv: JAH


from collections import Counter
from src.api_parser.vworld_api_parser import VworldOpenAPIParser
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

api_key = "2F23FA9B-2FB7-30B4-9335-A9D15732985F"
address1 = "인천 남동구 도림동"
address2 = "경기 남양주시 해밀예당1로 272"

parser = VworldOpenAPIParser(api_key)
admin_district_list = [admin for admin in parser.admin_district_by_addresses(address1, address2) if admin.area >= 100]

names = [ad.name for ad in admin_district_list]
geoms = [ad.geometry for ad in admin_district_list]
areas = [ad.area for ad in admin_district_list]
centroids = [ad.centroid for ad in admin_district_list]
