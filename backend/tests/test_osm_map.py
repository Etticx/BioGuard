import pytest
from pydantic import ValidationError
from reporting import Details
from test_reporting import setup,submit,details

POINT={"location_mode":"osm","map_id":"elmina-lakeside-v1","latitude":3.180661,"longitude":101.509091}

def test_osm_reports_require_in_bounds_coordinates_and_no_image_pin():
 assert Details.model_validate({**details(),**POINT}).latitude==POINT['latitude']
 for change in ({'latitude':None},{'latitude':0,'longitude':0},{'map_id':'other'},{'demo_pin':{'map_id':'elmina-city-centre-v1','x':0.5,'y':0.5}}):
  with pytest.raises(ValidationError):Details.model_validate({**details(),**POINT,**change})

def test_real_location_is_stored_and_returned_without_image_conversion(setup):
 client,ground,management,*_=setup
 result=submit(client,ground,identify_requested=False,**POINT)
 assert result.status_code==201,result.text
 saved=client.get('/reports/'+result.json()['id'],headers=management).json()
 for key,value in POINT.items():assert saved[key]==value
 assert saved.get('demo_pin') is None

def test_shared_map_allows_same_origin_embedding_and_tile_referrer_only(setup):
 client,*_=setup
 result=client.get('/maps/elmina')
 assert result.status_code==200
 assert result.headers['x-frame-options']=='SAMEORIGIN'
 assert result.headers['content-security-policy']=="frame-ancestors 'self'"
 assert result.headers['referrer-policy']=='strict-origin-when-cross-origin'
 assert client.get('/health').headers['x-frame-options']=='DENY'
 assert client.get('/officer-assets/vendor/leaflet/leaflet.js').status_code==200
