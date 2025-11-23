from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class AdministrativeDistrict:
    name: str
    code: str
    geometry: List[List[Tuple[float, float]]]
    area: float = 0.0
    centroid: Tuple[float, float] = (0.0, 0.0)
