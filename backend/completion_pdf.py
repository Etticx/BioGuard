"""Closed restoration case exports. Eligibility is shared by the UI and API."""
from io import BytesIO
from xml.sax.saxutils import escape


def eligible(report):
    jobs=report.get('work_items',[])
    restored=[w for w in jobs if w.get('work_type') in {'restoration','replanting'} and w.get('status')!='cancelled']
    return bool(report.get('status')=='completed' and restored
        and all(w.get('status')=='cancelled' or (w.get('status')=='verified' and (w.get('verification') or {}).get('decision')=='accept') for w in jobs)
        and all(any(f.get('followup_of')==w['id'] and f.get('status')=='verified' and (f.get('verification') or {}).get('decision')=='accept' for f in jobs) for w in restored))


def render(report, photo_loader):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether
    from reportlab.lib.pagesizes import A4
    from PIL import Image as PILImage, ImageOps
    green=colors.HexColor('#235b42');cream=colors.HexColor('#f7f8f4');ink=colors.HexColor('#1e2822')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleGreen',fontName='Helvetica-Bold',fontSize=25,leading=30,textColor=green,spaceAfter=14))
    styles.add(ParagraphStyle(name='SectionGreen',fontName='Helvetica-Bold',fontSize=13,leading=18,textColor=green,spaceBefore=18,spaceAfter=8,keepWithNext=True))
    styles.add(ParagraphStyle(name='BodyGreen',fontName='Helvetica',fontSize=10,leading=15,textColor=ink,spaceAfter=7,splitLongWords=True))
    styles.add(ParagraphStyle(name='CaptionGreen',fontSize=8,leading=12,textColor=colors.HexColor('#626b64'),spaceAfter=12))
    story=[]
    def text(value,style='BodyGreen'):
        safe=escape(str(value if value is not None else 'Not recorded')).replace('\n','<br/>')
        return Paragraph(safe,styles[style])
    def add(label,value):
        if value not in (None,'',[]):story.append(text(label+': '+str(value)))
    def section(title):story.append(text(title,'SectionGreen'))
    story.extend([text('Restoration completion report','TitleGreen'),text(report['reference'],'SectionGreen'),text('CLOSED - MANAGEMENT APPROVED')])
    section('Site and reported plant')
    for label,key in [('Site','site'),('Nearby landmark','landmark'),('Reported by','reporter_name'),('Observed on','observed_on'),('Submitted','created_at')]:add(label,report.get(key))
    prediction=report.get('prediction') or {}
    add('Model suggestion (reviewed separately)',prediction.get('predicted_species'))
    if report.get('latitude') is not None:
        add('Original map pin',f"{report['latitude']}, {report['longitude']}")
        url=f"https://www.openstreetmap.org/?mlat={report['latitude']}&mlon={report['longitude']}#map=18/{report['latitude']}/{report['longitude']}"
        story.append(Paragraph('<link href="'+escape(url,{'"':'&quot;'})+'" color="#235b42">View original location on OpenStreetMap</link>',styles['BodyGreen']))
    add('Original report note',report.get('notes'))
    for index,work in enumerate(report['work_items'],1):
        section(f"{index:02d}  "+('Follow-up inspection' if work.get('followup_of') else work['work_type'].replace('_',' ').title()))
        for label,key in [('Job reference','id'),('Ecology team','team_name'),('Scheduled date','due_on'),('Status','status'),('Confirmed species','confirmed_species'),('Removal plan','removal_instructions'),('Replacement species','replacement_species'),('Replanting plan','replanting_instructions'),('Work note','notes')]:add(label,work.get(key))
        if work.get('followup_of'):add('Previous restoration',work['followup_of'])
        plan=work.get('inspection') or (work.get('restoration_snapshot') or {}).get('inspection') or {}
        location=plan.get('location') or {}
        add('Inspection blocks',', '.join(location.get('block_ids',[])))
        add('Approved inspection guidance',plan.get('brief'))
        source=plan.get('source') or {}
        add('Guidance source',source.get('url'))
        for finding in work.get('inspections',[]):
            add('Inspection outcome',finding.get('outcome'));add('Inspection note',finding.get('notes'));add('Inspection review',finding.get('review_notes'))
        for completion in work.get('completions',[]):
            for label,key in [('Visit date','observed_on'),('Removed on','removed_on'),('Planted on','planted_on'),('Planted species','planted_species'),('Quantity planted','quantity'),('Target invasive regrowth','regrowth'),('Replacement condition','replacement_condition'),('Other suspected invasive plants','other_invasive'),('Field findings','notes'),('Submitted by','submitted_by')]:add(label,completion.get(key))
        verification=work.get('verification') or {}
        for label,key in [('Management decision','decision'),('Reviewed by','verified_by'),('Reviewed on','verified_at'),('Review note','notes')]:add(label,verification.get(key))
    section('Case activity')
    for item in report.get('history',[]):
        story.append(text(' | '.join(str(item[k]) for k in ('at','action','by','notes') if item.get(k)),'CaptionGreen'))
    photo_labels={}
    for work in report['work_items']:
        for visit in work.get('completions',[]):
            ids=visit.get('photo_ids',[])
            for i,photo_id in enumerate(ids):
                photo_labels[photo_id]=('Follow-up: current restored site' if i==0 else 'Follow-up: additional suspected plant') if work.get('followup_of') else ('After removal' if visit.get('stage')=='removal' or (visit.get('stage')=='both' and i==0) else 'After replanting' if visit.get('stage') in {'both','replanting'} else 'Inspection evidence')
    section('Photo evidence')
    for index,photo in enumerate(report.get('photos',[]),1):
        raw=photo_loader(photo['id'])
        if not raw:continue
        image=ImageOps.exif_transpose(PILImage.open(BytesIO(raw[1]))).convert('RGB');image.thumbnail((1400,1400))
        buffer=BytesIO();image.save(buffer,format='JPEG',quality=85);buffer.seek(0)
        w,h=image.size;scale=min(475/w,240/h)
        caption=f"Photo {index} - {photo_labels.get(photo['id'],photo.get('kind','evidence').replace('_',' '))}"+(f" | Job {photo['work_id']}" if photo.get('work_id') else ' | Original sighting')
        story.append(KeepTogether([Image(buffer,width=w*scale,height=h*scale,hAlign='LEFT'),Spacer(1,6),text(caption,'CaptionGreen')]))
    output=BytesIO()
    def page(canvas,doc):
        width,height=A4;canvas.saveState();canvas.setFillColor(cream);canvas.rect(0,height-65,width,65,fill=1,stroke=0)
        canvas.setFillColor(green);canvas.setFont('Helvetica-Bold',16);canvas.drawString(48,height-39,'BioGuard')
        canvas.setStrokeColor(green);canvas.line(48,42,width-48,42);canvas.setFont('Helvetica',8);canvas.setFillColor(ink)
        canvas.drawString(48,28,report['reference']+' | Completed restoration record');canvas.drawRightString(width-48,28,str(doc.page));canvas.restoreState()
    SimpleDocTemplate(output,pagesize=A4,leftMargin=48,rightMargin=48,topMargin=85,bottomMargin=60,title='BioGuard '+report['reference'],author='BioGuard').build(story,onFirstPage=page,onLaterPages=page)
    return output.getvalue()
