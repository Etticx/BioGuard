import json
import pytest
from pydantic import ValidationError
from reporting import Details
from test_reporting import setup,submit,details

PIN={"map_id":"elmina-city-centre-v1","x":0.72,"y":0.83}

def test_demo_mode_needs_a_valid_pin_not_fake_coordinates():
    base={**details(),"location_mode":"demo_map","demo_pin":PIN}
    assert Details.model_validate(base).demo_pin.x==0.72
    for change in ({"demo_pin":None},{"demo_pin":{**PIN,"x":1.2}},{"demo_pin":{**PIN,"map_id":"other"}},{"latitude":3.1,"longitude":101.5}):
        with pytest.raises(ValidationError):Details.model_validate({**base,**change})

def test_confirmed_demo_pin_is_saved_and_returned_to_management(setup):
    client,ground,management,*_=setup
    result=submit(client,ground,location_mode="demo_map",demo_pin=PIN,identify_requested=False)
    assert result.status_code==201,result.text
    report=result.json()
    saved=client.get('/reports/'+report['id'],headers=management).json()
    assert saved['demo_pin']==PIN
    assert saved['location_mode']=='demo_map'
    assert saved['latitude'] is None and saved['longitude'] is None

def test_missing_demo_pin_cannot_be_submitted(setup):
    client,ground,*_=setup
    assert submit(client,ground,location_mode="demo_map",identify_requested=False).status_code==422


def test_legacy_payload_keeps_its_original_idempotency_metadata(setup,monkeypatch):
    client,ground,_,_,_,app,*_=setup
    original=app.state.records.create_report
    captured=[]
    def capture(user,metadata,*args):
        captured.append(metadata.copy())
        return original(user,metadata,*args)
    monkeypatch.setattr(app.state.records,'create_report',capture)
    assert submit(client,ground,identify_requested=False).status_code==201
    assert 'demo_pin' not in captured[0] and 'location_mode' not in captured[0]
