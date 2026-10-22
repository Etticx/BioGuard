"""Offline evidence-based inspection prompts. No inference calls or spread predictions."""
import json
from pathlib import Path
ROOT=Path(__file__).parent
RULES=json.loads((ROOT/'inspection_rules.json').read_text(encoding='utf-8'))
AREAS=json.loads((ROOT.parent/'web/elmina-inspection-blocks.geojson').read_text(encoding='utf-8'))

def _ring(ring,p):
 inside=False
 for a,b in zip(ring,ring[1:]):
  dx,dy=b[0]-a[0],b[1]-a[1];length=(dx*dx+dy*dy)**.5
  if length and abs((p[0]-a[0])*dy-(p[1]-a[1])*dx)<=1e-10*length and min(a[0],b[0])-1e-10<=p[0]<=max(a[0],b[0])+1e-10 and min(a[1],b[1])-1e-10<=p[1]<=max(a[1],b[1])+1e-10:return 2
  if (a[1]>p[1])!=(b[1]>p[1]) and p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:inside=not inside
 return int(inside)

def _polygon(rings,p):
 outer=_ring(rings[0],p)
 if not outer:return 0
 for hole in rings[1:]:
  value=_ring(hole,p)
  if value==1:return 0
  if value==2:return 2
 return outer

def _contains(feature,p):
 g=feature['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
 return any(_polygon(poly,p) for poly in polys)

def location(report):
 from map_bounds import in_elmina
 lat,lon=report.get('latitude'),report.get('longitude')
 if report.get('location_mode')!='osm' or report.get('map_id')!='elmina-lakeside-v1' or not in_elmina(lat,lon):return {'kind':'unmapped','block_ids':[]}
 p=[lon,lat];water=[f for f in AREAS['features'] if f['properties']['type']=='water' and _contains(f,p)]
 if water:return {'kind':'water','block_ids':[],'water_names':[f['properties']['name'] for f in water]}
 blocks=sorted(f['properties']['block_id'] for f in AREAS['features'] if f['properties']['type']=='inspection_block' and _contains(f,p))
 return {'kind':'boundary' if len(blocks)>1 else 'block' if blocks else 'unmapped','block_ids':blocks}

def guidance(species,report):
 canonical=next((name for name in RULES if name.casefold()==species.strip().casefold()),None)
 if species.strip().casefold()=='sieruela rutidosperma':canonical='Cleome rutidosperma'
 base={'species':canonical or species,'location':location(report),'supported':bool(canonical),'limitations':['The block identifies the reported location, not infestation or predicted spread.','Guidance is a proposed interpretation of evidence, pending ecology review.']}
 if not canonical:return {**base,'source':None,'variables':{},'actions':['No reviewed inspection rule is available for this species. Obtain ecology guidance.']}
 rule=RULES[canonical];observed=report.get('inspection_observations') or {};variables={k:observed.get(k) if observed.get(k) in ('yes','no','unknown') else 'unknown' for k in rule['variables']}
 actions=[rule['actions'][k][v] for k,v in variables.items()] if variables else [rule['actions']['always']]
 return {**base,'source':rule['source'],'variables':variables,'actions':actions+['Photograph and pin additional plants found. Record none found if the inspection finds no additional plants.'],'limitations':base['limitations']+[rule['limitation']]}

def fallback_brief(bundle):
 area=' / '.join(bundle['location'].get('block_ids',[])) or ('mapped water location' if bundle['location']['kind']=='water' else 'reported location')
 return 'Inspection at '+area+' — '+bundle['species']+'.\n'+'\n'.join(str(i)+'. '+action for i,action in enumerate(bundle['actions'],1))
