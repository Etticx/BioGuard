"""Bounded public-page retrieval. No Groq calls, API keys or open-ended model tools."""
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

HERB_REFERENCES=(
 ("Kaempferia pulchra","https://www.nparks.gov.sg/florafaunaweb/flora/2/1/2166"),
 ("Centella asiatica","https://www.nparks.gov.sg/florafaunaweb/flora/5/3/5347"),
)
WOODY_REFERENCES=(("Syzygium myrtifolium","https://www.nparks.gov.sg/florafaunaweb/flora/3/1/3156"),)
WOODY={"leucaena leucocephala","psidium guajava","muntingia calabura","ficus microcarpa","macaranga tanarius"}
_cache={}
_lock=threading.Lock()

class PageText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in {"script","style","noscript","svg"}:self.hidden+=1
    def handle_endtag(self,tag):
        if tag in {"script","style","noscript","svg"}:self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden and data.strip():self.parts.append(" ".join(data.split()))


def read_reference(item):
    name,url=item
    with _lock:
        cached=_cache.get(url)
        if cached and monotonic()-cached[0]<(21600 if cached[1] else 60):return cached[1]
    result=None
    try:
        request=Request(url,headers={"User-Agent":"BioGuard/0.2 (botanical reference reader)","Accept":"text/html"})
        with urlopen(request,timeout=8) as response:
            final=urlsplit(response.geturl())
            if final.scheme!="https" or final.hostname not in {urlsplit(url).hostname,"www.nparks.gov.sg","nparks.gov.sg"}:return None
            raw=response.read(768001)
        if len(raw)>768000:return None
        parser=PageText();parser.feed(raw.decode("utf-8",errors="replace"))
        text="\n".join(parser.parts)
        if not all(word.casefold() in text.casefold() for word in name.split()[:2]):return None
        excerpts=[]
        for term in ("Native Distribution","Plant Growth Form","Cultivation","Light Preference","Water Preference","Rootzone Tolerance","Landscape Uses","control","removal"):
            match=re.search(re.escape(term),text,re.I)
            if match:excerpts.append(text[max(0,match.start()-40):match.start()+550])
        if excerpts:
            result={"url":url,"title":name+" â€” botanical profile","text":name+"\n"+"\n".join(excerpts)[:3300]}
    except (OSError,ValueError):pass
    finally:
        with _lock:_cache[url]=(monotonic(),result)
    return result


def load_references(context):
    species=context.get("confirmed_species","").strip()
    base=" ".join(species.casefold().split()[:2])
    selected=list(WOODY_REFERENCES if base in WOODY else HERB_REFERENCES)
    replacements={url:name for name,url in selected}
    catalog=json.loads((Path(__file__).parent/"species_catalog.json").read_text(encoding="utf-8"))
    for scientific,entry in catalog.items():
        url=entry.get("common_name_source","")
        if scientific.casefold()==base and urlsplit(url).hostname=="www.nparks.gov.sg" and not urlsplit(url).path.endswith(".pdf"):
            selected.append((scientific,url));break
    with ThreadPoolExecutor(max_workers=3) as pool:
        sources=[source for source in pool.map(read_reference,selected) if source]
    return [{**source,"id":index+1,**({"replacement_species":replacements[source["url"]]} if source["url"] in replacements else {})}
            for index,source in enumerate(sources)]
