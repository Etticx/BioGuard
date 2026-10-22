"""Approved inspection snapshots and additional sightings. Never authorises removal."""
import json
from uuid import uuid4
from operations import now,conflict
from inspection_guidance import guidance

def snapshot(brief,species,report,user):
    bundle=guidance(species,report)
    if not bundle['supported']:raise ValueError('No sourced inspection guidance is available for this species.')
    point={key:report.get(key) for key in ('latitude','longitude','map_id','location_mode')}
    return {'brief':brief,'species':bundle['species'],'location':bundle['location'],'point':point,'source':bundle['source'],'boundary_version':'elmina-inspection-blocks-v1','approved_by':user['display_name'],'approved_at':now()}

class InspectionResultsMixin:
    def record_inspection(self,identifier,work_id,user,details,photos,digest):
        if user['role']!='ecology':raise ValueError('Only ecology can submit inspection results.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            work=db.execute('SELECT * FROM work_items WHERE id=? AND report_id=?',(work_id,identifier)).fetchone()
            if not work or work['team_id']!=user.get('team_id'):return None
            if not db.execute("SELECT id FROM teams WHERE id=? AND role='ecology' AND active=1",(work['team_id'],)).fetchone():return None
            data=json.loads(work['data'])
            previous=next((v for v in data.get('inspections',[]) if v['request_key']==details['request_key']),None)
            if previous:
                if previous['digest']!=digest:conflict('This inspection submission key was already used for different content.')
                return self.get_report(identifier,user)
            if work['revision']!=details['revision'] or work['status'] not in {'accepted','in_progress','blocked','correction_requested'}:conflict('Refresh this job before recording inspection results.')
            if not data.get('inspection'):raise ValueError('Management must save inspection instructions for this job first.')
            if len(photos)!=len(details['findings']):raise ValueError('Each additional plant needs a photo and pin.')
            item={**details,'id':uuid4().hex,'digest':digest,'submitted_at':now(),'submitted_by':user['display_name'],'species':data['inspection']['species'],'review_status':'pending','photo_ids':[]}
            for finding,(mime,content) in zip(item['findings'],photos):
                photo_id=uuid4().hex;finding['photo_id']=photo_id;finding['status']='needs_management_review';item['photo_ids'].append(photo_id)
                db.execute('INSERT INTO photos(id,report_id,kind,mime,content,work_id) VALUES (?,?,?,?,?,?)',(photo_id,identifier,'inspection_finding',mime,content,work_id))
            data.setdefault('inspections',[]).append(item)
            data.setdefault('history',[]).append({'at':now(),'action':'inspection_submitted','by':user['display_name'],'notes':details['notes']})
            db.execute('UPDATE work_items SET revision=revision+1,updated_at=?,data=? WHERE id=?',(now(),json.dumps(data),work_id))
            row=db.execute('SELECT * FROM reports WHERE id=?',(identifier,)).fetchone()
            self.event(db,row,json.loads(row['data']),'inspection_submitted',user,details['notes'])
            self.emit(db,'inspection_'+item['id'],identifier,'Ecology submitted inspection results for review.',role='management')
        return self.get_report(identifier,user)

    def review_inspection(self,identifier,work_id,user,details):
        if user['role']!='management':raise ValueError('Only management can review inspection results.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            work=db.execute('SELECT * FROM work_items WHERE id=? AND report_id=?',(work_id,identifier)).fetchone()
            if not work:return None
            if work['revision']!=details['revision']:conflict('Refresh this job before reviewing inspection results.')
            data=json.loads(work['data']);item=next((v for v in data.get('inspections',[]) if v['id']==details['inspection_id']),None)
            if not item:return None
            if item['review_status']=='reviewed':conflict('This inspection has already been reviewed.')
            item.update(review_status='reviewed',review_notes=details['notes'],reviewed_by=user['display_name'],reviewed_at=now())
            db.execute('UPDATE work_items SET revision=revision+1,updated_at=?,data=? WHERE id=?',(now(),json.dumps(data),work_id))
            row=db.execute('SELECT * FROM reports WHERE id=?',(identifier,)).fetchone();self.event(db,row,json.loads(row['data']),'inspection_reviewed',user,details['notes'])
            self.emit(db,'inspection_review_'+item['id'],identifier,'Management reviewed the inspection results.',team_id=work['team_id'])
        return self.get_report(identifier,user)
