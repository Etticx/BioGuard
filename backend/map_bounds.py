"""Shared pilot boundary. It is a demo extent, not a surveyed SDP property boundary."""
import json,math
from pathlib import Path
CONFIG=json.loads((Path(__file__).parent.parent/'web'/'elmina-map-config.json').read_text(encoding='utf-8'))
def in_elmina(latitude,longitude):
    if latitude is None or longitude is None:return False
    south_west,north_east=CONFIG['bounds']
    return math.isfinite(latitude) and math.isfinite(longitude) and south_west[0]<=latitude<=north_east[0] and south_west[1]<=longitude<=north_east[1]
