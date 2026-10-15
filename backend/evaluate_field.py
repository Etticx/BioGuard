"""Evaluate reviewed new field photos; this never trains or changes the model."""
import argparse
from collections import Counter
from datetime import date
from hashlib import sha256
from pathlib import Path
import json
from predictor import BioGuardPredictor

IMAGE_EXTENSIONS={".jpg",".jpeg",".png",".webp"}
def evaluate(manifest,model_dir,exclude_root=None):
    manifest=Path(manifest).resolve();values=json.loads(manifest.read_text('utf-8'));cases=values.get('cases',[])
    if not cases:raise ValueError('Add independently reviewed new field photos first.')
    predictor=BioGuardPredictor(model_dir)
    known={name.replace('_',' ') for name in predictor.classes}
    forbidden=set()
    if exclude_root and Path(exclude_root).is_dir():
        forbidden={sha256(p.read_bytes()).hexdigest() for p in Path(exclude_root).rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS}
    seen=set();sources=set();results=[]
    for item in cases:
        if any(not item.get(key) or 'REPLACE' in str(item[key]) for key in ('reviewed_label','reviewed_by','site','source_id')):raise ValueError('Every image needs a reviewer, label, site and unique source ID.')
        date.fromisoformat(item['capture_date'])
        source=(manifest.parent/item['path']).resolve(strict=True)
        if exclude_root and source.is_relative_to(Path(exclude_root).resolve()):raise ValueError('Use fresh photos outside the training image folder.')
        content=source.read_bytes();digest=sha256(content).hexdigest()
        if digest in seen or digest in forbidden or item['source_id'] in sources:raise ValueError('Repeated/training image or source found. Keep captures from one source in one evaluation group.')
        seen.add(digest);sources.add(item['source_id'])
        label=item['reviewed_label']
        if label not in known and label!='unsupported':raise ValueError('Use a supported scientific name or unsupported.')
        result=predictor.predict(content)
        results.append({'source_id':item['source_id'],'sha256':digest,'reviewed_label':label,'site':item['site'],'correct':result['predicted_species']==label,'prediction':result})
    supported=[r for r in results if r['reviewed_label']!='unsupported'];unsupported=[r for r in results if r['reviewed_label']=='unsupported']
    scores=[]
    for label in sorted({r['reviewed_label'] for r in supported}):
        tp=sum(r['reviewed_label']==label and r['prediction']['predicted_species']==label for r in supported)
        fp=sum(r['reviewed_label']!=label and r['prediction']['predicted_species']==label for r in supported)
        fn=sum(r['reviewed_label']==label and r['prediction']['predicted_species']!=label for r in supported)
        scores.append({'species':label,'photos':sum(r['reviewed_label']==label for r in supported),'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0})
    return {'photos':len(results),'known_accuracy':sum(r['correct'] for r in supported)/len(supported) if supported else None,'macro_f1_present_species':sum(s['f1'] for s in scores)/len(scores) if scores else None,'species':scores,'unsupported_photos':len(unsupported),'unsupported_confident_matches':sum(not r['prediction']['uncertain_identification'] for r in unsupported),'uncertain_known_photos':sum(r['prediction']['uncertain_identification'] for r in supported),'sites':dict(Counter(r['site'] for r in results)),'review_threshold':predictor.review_threshold,'model_sha256':predictor.model_sha256,'cases':results,'scope':'Server evaluation of supplied image bytes; physical phone JPEG/camera checks are separate. unsupported is an evaluation label, not a trained output class.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('manifest',type=Path);parser.add_argument('--model-dir',type=Path,default=Path(__file__).parent/'model');parser.add_argument('--exclude-root',type=Path,default=Path(__file__).parent.parent.parent/'SDHackathon/data/bioguard/raw');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=evaluate(args.manifest,args.model_dir,args.exclude_root);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),'utf-8');print(f"Evaluated {result['photos']} new field photos; saved {args.output}")
