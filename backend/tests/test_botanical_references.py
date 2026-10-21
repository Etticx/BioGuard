"""Reference retrieval is independent of Groq and never receives its credential."""
import botanical_references as refs


def test_official_page_is_read_once_and_cached_without_authorization(monkeypatch):
    refs._cache.clear();calls=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def geturl(self):return refs.HERB_REFERENCES[1][1]
        def read(self,size):return b"<html><h1>Centella asiatica</h1><p>Native Distribution: Malaysia</p><p>Light Preference: Semi Shade</p><script>SECRET SCRIPT TEXT</script></html>"
    def opening(request,**kwargs):
        assert request.get_header('Authorization') is None
        calls.append(request.full_url);return Response()
    monkeypatch.setattr(refs,'urlopen',opening)
    first=refs.read_reference(refs.HERB_REFERENCES[1]);second=refs.read_reference(refs.HERB_REFERENCES[1])
    assert first==second and len(calls)==1
    assert 'Malaysia' in first['text'] and 'SECRET SCRIPT TEXT' not in first['text']


def test_unreadable_page_does_not_become_botanical_evidence(monkeypatch):
    refs._cache.clear()
    def failed(*a,**k):raise OSError('Synthetic network failure')
    monkeypatch.setattr(refs,'urlopen',failed)
    assert refs.read_reference(refs.HERB_REFERENCES[0]) is None
