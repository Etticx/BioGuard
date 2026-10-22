from test_reporting import setup
from test_upcoming_followup import approved,findings
from test_workflow import accept,verify
from completion_pdf import eligible


def test_pdf_only_for_management_after_final_followup_review(setup):
    client,ground,manager,_,_,_,ecology,_=setup
    report=approved(setup)
    path='/reports/'+report['id']+'/completion.pdf'
    assert client.get(path).status_code==401
    assert client.get(path,headers=ground).status_code==403
    assert client.get(path,headers=ecology).status_code==403
    assert client.get(path,headers=manager).status_code==409
    report=accept(client,ecology,report)
    report=findings(setup,report).json()
    assert client.get(path,headers=manager).status_code==409
    report=verify(client,manager,report).json()
    assert report['completion_pdf_available'] is True
    response=client.get(path,headers=manager)
    assert response.status_code==200,response.text
    assert response.content.startswith(b'%PDF-')
    assert response.headers['content-type']=='application/pdf'
    assert 'attachment;' in response.headers['content-disposition']
    assert response.headers['cache-control']=='no-store'
    assert len(response.content)>2000
    import os
    if os.environ.get('BIOGUARD_PDF_TEST_PREVIEW'):
        from pathlib import Path
        Path(os.environ['BIOGUARD_PDF_TEST_PREVIEW']).write_bytes(response.content)


def test_cancelled_closed_without_work_and_incomplete_chains_have_no_pdf():
    assert not eligible({'status':'closed','work_items':[]})
    assert not eligible({'status':'cancelled','work_items':[]})
    restoration={'id':'restore','work_type':'restoration','status':'verified','verification':{'decision':'accept'}}
    assert not eligible({'status':'completed','work_items':[restoration]})
    followup={'id':'inspect','work_type':'inspection','followup_of':'restore','status':'awaiting_verification'}
    assert not eligible({'status':'completed','work_items':[restoration,followup]})
    followup.update(status='verified',verification={'decision':'accept'})
    assert eligible({'status':'completed','work_items':[restoration,followup]})
