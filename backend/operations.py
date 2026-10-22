"""Workflow upgrades. All state transitions and their audit records commit together."""
from field_clock import field_today
from contextlib import closing
from datetime import date, datetime, timezone, timedelta
from hashlib import sha256
import json
from pathlib import Path
import secrets
import sqlite3
import time
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


def conflict(message):
    # Imported lazily to keep the base store and this mixin independent at import time.
    from records import RecordConflict
    raise RecordConflict(message)


def require_inspection_day(data):
    if data.get("followup_of") and data.get("due_on") != field_today().isoformat():
        raise ValueError("This inspection can only be updated on its scheduled date (Malaysia time). Ask management to reschedule a missed visit.")


TERMINAL = {"verified", "cancelled"}


class OperationsMixin:
    def initialize(self, seed=True, temporary_seed=False):
        super().initialize(False)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS teams (id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL,active INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS sites (id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL,active INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS blocks (id TEXT PRIMARY KEY,site_id TEXT NOT NULL REFERENCES sites(id),name TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,UNIQUE(site_id,name));
                CREATE TABLE IF NOT EXISTS work_items (id TEXT PRIMARY KEY,report_id TEXT NOT NULL REFERENCES reports(id),team_id TEXT NOT NULL REFERENCES teams(id),status TEXT NOT NULL,revision INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY,event_key TEXT UNIQUE NOT NULL,report_id TEXT REFERENCES reports(id),role TEXT,team_id TEXT,user_id TEXT,message TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS notice_reads (notice_id TEXT NOT NULL REFERENCES notices(id),user_id TEXT NOT NULL REFERENCES users(id),read_at TEXT NOT NULL,PRIMARY KEY(notice_id,user_id));
                CREATE TABLE IF NOT EXISTS admin_audit (id TEXT PRIMARY KEY,actor_id TEXT,action TEXT NOT NULL,target_id TEXT,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL);
            """)
            additions={"users":{"team_id":"TEXT","active":"INTEGER NOT NULL DEFAULT 1","must_change_password":"INTEGER NOT NULL DEFAULT 0"},
                       "reports":{"reporter_group_id":"TEXT","assigned_group_id":"TEXT"},"photos":{"work_id":"TEXT"},"teams":{"role":"TEXT NOT NULL DEFAULT 'ground'"}}
            for table,columns in additions.items():
                existing={row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                for column,definition in columns.items():
                    if column not in existing: db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            # Migrate permissions by stored role, never by account name; IDs and sessions survive.
            db.execute("UPDATE users SET role='management' WHERE role='officer'")
            db.execute("UPDATE notices SET role='management' WHERE role='officer'")
            for user in db.execute("SELECT * FROM users WHERE role IN ('ground','ecology') AND team_id IS NULL").fetchall():
                name=user["display_name"]
                if db.execute("SELECT id FROM teams WHERE name=?",(name,)).fetchone():name += " " + user["id"][:5]
                db.execute("INSERT OR IGNORE INTO teams(id,name,role) VALUES (?,?,?)",(user["id"],name,user["role"]))
                db.execute("UPDATE users SET team_id=? WHERE id=?",(user["id"],user["id"]))
            db.execute("UPDATE reports SET reporter_group_id=(SELECT team_id FROM users WHERE id=reports.reporter_id) WHERE reporter_group_id IS NULL")
            db.execute("UPDATE reports SET assigned_group_id=(SELECT team_id FROM users WHERE id=reports.assigned_team_id) WHERE assigned_group_id IS NULL AND assigned_team_id IS NOT NULL")
            for report in db.execute("SELECT * FROM reports WHERE status='assigned'").fetchall():
                if db.execute("SELECT id FROM work_items WHERE report_id=?",(report["id"],)).fetchone():continue
                review=json.loads(report["data"]).get("review") or {}
                if not report["assigned_group_id"]:continue
                work={**review,"work_type":"removal_replanting","due_on":None,"priority":"normal","completions":[],"verification":None,"history":[{"at":report["updated_at"],"action":"legacy_assignment_imported"}]}
                db.execute("INSERT INTO work_items VALUES (?,?,?,?,?,?,?,?)",(uuid4().hex,report["id"],report["assigned_group_id"],"assigned",1,report["updated_at"],report["updated_at"],json.dumps(work)))
            empty=db.execute("SELECT COUNT(*) FROM users").fetchone()[0]==0
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('schema_version','3')")
        if seed and empty:
            accounts=[]
            for username,display,role in (("grounds","Ground team","ground"),("ecology","Ecology field team","ecology"),("management","Management","management")):
                password=secrets.token_urlsafe(15)
                self.add_user(username,password,display,role,must_change=True)
                accounts.append({"username":username,"password":password,"display_name":display,"role":role})
            (self.directory/"local-accounts.json").write_text(json.dumps(accounts,indent=2),"utf-8")

    def add_user(self, username, password, display_name, role, team_id=None, must_change=False):
        from records import password_hash
        if role not in {"ground","ecology","management"}:raise ValueError("Choose ground, ecology or management.")
        username=username.strip().lower()
        if not username or len(username)>80 or len(password)<10:raise ValueError("Use a username and a password of at least 10 characters.")
        identifier,salt=uuid4().hex,secrets.token_hex(16)
        with self.connect() as db:
            if role in {"ground","ecology"} and not team_id:
                team_id=identifier
                db.execute("INSERT INTO teams(id,name,role) VALUES (?,?,?)",(team_id,display_name+" "+identifier[:4] if db.execute("SELECT id FROM teams WHERE name=?",(display_name,)).fetchone() else display_name,role))
            if role in {"ground","ecology"} and not db.execute("SELECT id FROM teams WHERE id=? AND active=1 AND role=?",(team_id,role)).fetchone():raise ValueError("Choose an active team matching this staff role.")
            try:db.execute("INSERT INTO users(id,username,display_name,role,salt,password_hash,team_id,must_change_password) VALUES (?,?,?,?,?,?,?,?)",(identifier,username,display_name,role,salt,password_hash(password,salt),team_id if role in {"ground","ecology"} else None,int(must_change)))
            except sqlite3.IntegrityError as error:raise ValueError("That username is already in use.") from error
        return identifier

    @staticmethod
    def public_user(row):
        return {key:row[key] for key in ("id","username","display_name","role","team_id","must_change_password")}

    def login(self, username, password):
        with self.connect() as db:
            user=db.execute("SELECT active FROM users WHERE username=?",(username,)).fetchone()
            if user and not user["active"]:return None
        return super().login(username,password)

    def session_user(self, token):
        user=super().session_user(token)
        if user:
            with self.connect() as db:
                active=db.execute("SELECT active FROM users WHERE id=?",(user["id"],)).fetchone()
            if not active or not active["active"]:return None
        return user

    def teams(self):
        with self.connect() as db:
            return [{**dict(row),"display_name":row["name"]} for row in db.execute("SELECT teams.*,COUNT(users.id) AS members FROM teams JOIN users ON users.team_id=teams.id AND users.active=1 AND users.role='ecology' WHERE teams.active=1 AND teams.role='ecology' GROUP BY teams.id ORDER BY teams.name")]

    def can_access(self, row, user):
        if user["role"]=="management":return True
        if user["role"]=="ground":
            return row["reporter_id"]==user["id"] or bool(user.get("team_id") and user["team_id"]==row["reporter_group_id"])
        if user["role"]!="ecology" or not user.get("team_id"):return False
        with self.connect() as db:
            return bool(db.execute("SELECT work_items.id FROM work_items JOIN teams ON teams.id=work_items.team_id WHERE work_items.report_id=? AND work_items.team_id=? AND teams.role='ecology'",(row["id"],user["team_id"])).fetchone())

    def emit(self, db, key, report_id, message, role=None, team_id=None, user_id=None):
        db.execute("INSERT OR IGNORE INTO notices VALUES (?,?,?,?,?,?,?,?)",(uuid4().hex,key,report_id,role,team_id,user_id,message,now()))

    def event(self, db, row, data, action, user, notes="", status=None, group_id="unchanged"):
        timestamp=now()
        data.setdefault("history",[]).append({"at":timestamp,"action":action,"by":user["display_name"],"notes":notes})
        db.execute("UPDATE reports SET status=?,revision=revision+1,updated_at=?,data=? WHERE id=?",(status or row["status"],timestamp,json.dumps(data),row["id"]))
        if group_id!="unchanged":db.execute("UPDATE reports SET assigned_group_id=? WHERE id=?",(group_id,row["id"]))

    def create_report(self,user,details,prediction,provenance,photos,request_key,digest):
        if user["role"]!="ground":raise ValueError("Only the ground team can submit sightings.")
        result=super().create_report(user,details,prediction,provenance,photos,request_key,digest)
        with self.connect() as db:
            db.execute("UPDATE reports SET reporter_group_id=COALESCE(reporter_group_id,?) WHERE id=?",(user.get("team_id"),result["id"]))
            self.emit(db,"submitted_"+result["id"],result["id"],"New sighting needs management review.",role="management")
        return self.get_report(result["id"],user)

    def get_report(self,identifier,user):
        report=super().get_report(identifier,user)
        if not report:return None
        with self.connect() as db:
            row=db.execute("SELECT assigned_group_id,reporter_group_id FROM reports WHERE id=?",(identifier,)).fetchone()
            report["assigned_team_id"]=row["assigned_group_id"]
            report["reporter_team_id"]=row["reporter_group_id"]
            report["work_items"]=[self.work_value(work,db) for work in db.execute("SELECT * FROM work_items WHERE report_id=? ORDER BY created_at",(identifier,))]
            report["photos"]=[{"id":p["id"],"kind":p["kind"],"work_id":p["work_id"],"url":f"/reports/{identifier}/photos/{p['id']}"} for p in db.execute("SELECT id,kind,work_id FROM photos WHERE report_id=? ORDER BY rowid",(identifier,))]
        if user["role"]!="management":
            # The complete audit remains stored; field evidence notes belong to its work team.
            report["history"]=[event if event.get("action") in {"submitted","information_added"} else {key:value for key,value in event.items() if key!="notes"} for event in report.get("history",[])]
        if user["role"]=="ground":
            report["work_items"]=[]
            report["photos"]=[photo for photo in report["photos"] if not photo["work_id"]]
            review=report.get("review")
            report["review"]={key:review.get(key) for key in ("decision","notes","reviewer_name")} if review and review.get("decision") in {"request_info","no_action"} else None
        elif user["role"]=="ecology":
            report["work_items"]=[work for work in report["work_items"] if work["team_id"]==user.get("team_id")]
            for work in report["work_items"]:
                verification=work.get("verification")
                if verification and (verification.get("next_plan") or {}).get("assigned_team_id")!=user.get("team_id"):
                    verification.pop("next_plan",None)
            own={work["id"] for work in report["work_items"]}
            report["photos"]=[photo for photo in report["photos"] if not photo["work_id"] or photo["work_id"] in own]
            if (report.get("review") or {}).get("assigned_team_id")!=user.get("team_id"):report["review"]=None
        from completion_pdf import eligible
        report["completion_pdf_available"]=eligible(report)
        return report

    def get_photo(self,report_id,photo_id,user):
        report=self.get_report(report_id,user)
        if not report or photo_id not in {photo["id"] for photo in report["photos"]}:return None
        return super().get_photo(report_id,photo_id,user)

    def work_value(self,row,db):
        value=json.loads(row["data"])
        value.update({key:row[key] for key in ("id","report_id","team_id","status","revision","created_at","updated_at")})
        team=db.execute("SELECT name,role FROM teams WHERE id=?",(row["team_id"],)).fetchone()
        value["team_name"]=team[0] if team else "Former team"
        value["inspection_open_today"]=not value.get("followup_of") or value.get("due_on")==field_today().isoformat()
        value["legacy"]=value.get("work_type") not in {"restoration","inspection","removal","replanting"}
        value["requires_reassignment"]=row["status"] not in TERMINAL and (not team or team["role"]!="ecology")
        value["overdue"]=bool(value.get("due_on") and value["due_on"]<field_today().isoformat() and row["status"] not in TERMINAL | {"awaiting_verification"})
        return value

    def list_reports(self,user):
        with self.connect() as db:
            rows=db.execute("SELECT * FROM reports ORDER BY updated_at DESC").fetchall()
            identifiers=[row["id"] for row in rows if self.can_access(row,user)]
        return [self.get_report(identifier,user) for identifier in identifiers]

    def new_work(self,db,report_id,team_id,plan,user):
        if user["role"]!="management":raise ValueError("Only management can assign work.")
        if plan.get("work_type") not in {"restoration","inspection","removal","replanting"}:raise ValueError("Choose an approved restoration job.")
        if not db.execute("SELECT teams.id FROM teams JOIN users ON users.team_id=teams.id WHERE teams.id=? AND teams.active=1 AND teams.role='ecology' AND users.active=1 AND users.role='ecology'",(team_id,)).fetchone():raise ValueError("Choose an active ecology team with at least one active ecology member.")
        if plan.get("work_type")=="restoration" and (plan.get("confirmed_invasive") is not True or not all(plan.get(key) for key in ("confirmed_species","removal_instructions","replacement_species","replanting_instructions")) or plan["confirmed_species"].strip().lower()=="unknown"):
            raise ValueError("Approve the invasive species, removal instructions and replacement planting plan.")
        identifier,timestamp=uuid4().hex,now()
        data={**plan,"completions":[],"verification":None,"history":[{"at":timestamp,"action":"assigned","by":user["display_name"]}]}
        if plan.get('inspection_brief'):
            from inspection_results import snapshot
            report_data=json.loads(db.execute('SELECT data FROM reports WHERE id=?',(report_id,)).fetchone()[0])
            data['inspection']=snapshot(plan['inspection_brief'],plan['confirmed_species'],report_data,user)
        db.execute("INSERT INTO work_items VALUES (?,?,?,?,?,?,?,?)",(identifier,report_id,team_id,"assigned",1,timestamp,timestamp,json.dumps(data)))
        self.emit(db,"work_"+identifier,report_id,"A field visit has been assigned to your team.",team_id=team_id)
        return identifier

    def review_report(self,identifier,user,review):
        if user["role"]!="management":raise ValueError("Only management can review reports.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM reports WHERE id=?",(identifier,)).fetchone()
            if not row:return None
            if row["revision"]!=review["revision"]:conflict("This report changed. Refresh before reviewing.")
            data=json.loads(row["data"]);decision=review["decision"]
            active=db.execute("SELECT id FROM work_items WHERE report_id=? AND status NOT IN ('verified','cancelled')",(identifier,)).fetchall()
            if decision=="assign":
                if active:conflict("Revise or cancel the active visit before assigning another.")
                self.new_work(db,identifier,review["assigned_team_id"],review,user)
                team=db.execute("SELECT name FROM teams WHERE id=?",(review["assigned_team_id"],)).fetchone()
                data["review"]={**review,"assigned_team_name":team[0],"reviewer_name":user["display_name"],"reviewed_at":now()}
                self.event(db,row,data,"assigned",user,review["notes"],"assigned",review["assigned_team_id"])
            elif decision in {"cancel","duplicate"}:
                if decision=="duplicate":
                    if db.execute("SELECT id FROM reports WHERE status='duplicate' AND json_extract(data,'$.duplicate_of')=?",(identifier,)).fetchone():raise ValueError("Other sightings link to this original. Reopen those duplicates before linking this case elsewhere.")
                    target=review.get("duplicate_of")
                    if not target or target==identifier or not db.execute("SELECT id FROM reports WHERE id=? AND status!='duplicate'",(target,)).fetchone():raise ValueError("Choose a different, existing report that is not itself a duplicate.")
                    data["duplicate_of"]=target
                for work in active:
                    current=db.execute("SELECT data FROM work_items WHERE id=?",(work["id"],)).fetchone()
                    work_data=json.loads(current[0]);work_data["history"].append({"at":now(),"action":"cancelled","by":user["display_name"],"notes":review["notes"]})
                    db.execute("UPDATE work_items SET status='cancelled',revision=revision+1,updated_at=?,data=? WHERE id=?",(now(),json.dumps(work_data),work["id"]))
                self.event(db,row,data,decision,user,review["notes"],"duplicate" if decision=="duplicate" else "cancelled")
                if row["assigned_group_id"]:self.emit(db,f"cancel_{identifier}_{row['revision']}",identifier,"Management cancelled or linked this case. Check the latest instructions.",team_id=row["assigned_group_id"])
            elif decision=="reopen":
                if active:conflict("This report already has an active visit.")
                data.pop("duplicate_of",None)
                self.event(db,row,data,"reopened",user,review["notes"],"submitted")
            else:
                if active:conflict("An active visit exists. Cancel it before closing or requesting report information.")
                status="closed" if decision=="no_action" else "needs_info"
                data["review"]={**review,"reviewer_name":user["display_name"],"reviewed_at":now()}
                self.event(db,row,data,status,user,review["notes"],status)
                self.emit(db,f"review_{identifier}_{row['revision']}",identifier,"Management reviewed your report. "+("More information is needed." if status=="needs_info" else "No field work is required."),team_id=row["reporter_group_id"],user_id=None if row["reporter_group_id"] else row["reporter_id"])
        return self.get_report(identifier,user)

    def revise_work(self,identifier,work_id,user,revision,plan):
        if user["role"]!="management":raise ValueError("Only management can revise work.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM reports WHERE id=?",(identifier,)).fetchone()
            work=db.execute("SELECT * FROM work_items WHERE id=? AND report_id=?",(work_id,identifier)).fetchone()
            if not row or not work:return None
            if work["revision"]!=revision or work["status"] not in {"assigned","accepted","in_progress","blocked","correction_requested"}:conflict("This visit changed or is awaiting verification. Refresh it first.")
            team_id=plan["assigned_team_id"]
            if not db.execute("SELECT teams.id FROM teams JOIN users ON users.team_id=teams.id WHERE teams.id=? AND teams.active=1 AND teams.role='ecology' AND users.active=1 AND users.role='ecology'",(team_id,)).fetchone():raise ValueError("Choose a staffed, active ecology team.")
            data=json.loads(work["data"])
            if data.get("work_type") not in {"restoration","inspection","removal","replanting"}:raise ValueError("This historical visit is read-only. Cancel it and assign a new visit.")
            if data["completions"] and data["work_type"] != plan["work_type"]:
                raise ValueError("Keep the visit type after evidence has been submitted. Cancel and create a new visit to change it.")
            if data.get("followup_of") and plan["work_type"]!="inspection":raise ValueError("Keep this follow-up as an inspection; approve corrective work after reviewing findings.")
            previous_team=work["team_id"]
            if plan.get('inspection_brief'):
                from inspection_results import snapshot
                data['inspection']=snapshot(plan['inspection_brief'],plan['confirmed_species'],json.loads(row['data']),user)
            elif data.get('inspection') and data['inspection']['species'].casefold()!=plan.get('confirmed_species','').casefold():
                data.pop('inspection',None)
            data.update(plan)
            data["history"].append({"at":now(),"action":"instructions_revised","by":user["display_name"],"notes":plan["notes"]})
            db.execute("UPDATE work_items SET team_id=?,status='assigned',revision=revision+1,updated_at=?,data=? WHERE id=?",(team_id,now(),json.dumps(data),work_id))
            report_data=json.loads(row["data"]);report_data["review"]={**plan,"reviewer_name":user["display_name"],"reviewed_at":now()}
            self.event(db,row,report_data,"work_revised",user,plan["notes"],"assigned",team_id)
            self.emit(db,f"revised_{work_id}_{revision}",identifier,"Your team's visit instructions have changed.",team_id=team_id)
            if previous_team!=team_id:
                self.emit(db,f"reassigned_{work_id}_{revision}",None,"A visit previously assigned to your team has been reassigned.",team_id=previous_team)
        return self.get_report(identifier,user)

    def progress_work(self,identifier,work_id,user,revision,action,notes):
        if user["role"]!="ecology":raise ValueError("Only the ecology field team can update work.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            work=db.execute("SELECT * FROM work_items WHERE id=? AND report_id=?",(work_id,identifier)).fetchone()
            if not work or work["team_id"]!=user.get("team_id"):return None
            if not db.execute("SELECT teams.id FROM teams JOIN users ON users.team_id=teams.id WHERE teams.id=? AND teams.role='ecology' AND teams.active=1 AND users.id=? AND users.role='ecology' AND users.active=1",(work["team_id"],user["id"])).fetchone():return None
            if work["revision"]!=revision or work["status"] not in {"assigned","accepted","in_progress","correction_requested","blocked"}:conflict("Refresh this visit before updating it.")
            data=json.loads(work["data"])
            require_inspection_day(data)
            if data.get("work_type") not in {"restoration","inspection","removal","replanting"}:raise ValueError("This historical visit is read-only. Ask management for a new assignment.")
            if action=="accept":
                if work["status"]!="assigned":conflict("This job has already been accepted. Refresh it.")
                status="accepted"
            elif action=="start":
                if work["status"]=="assigned":conflict("Accept this job before starting work.")
                status="in_progress"
            elif action=="blocked":
                if work["status"]=="assigned":conflict("Accept this job before updating it.")
                status="blocked"
            else:raise ValueError("Choose accept, start or blocked.")
            data["history"].append({"at":now(),"action":status,"by":user["display_name"],"notes":notes})
            db.execute("UPDATE work_items SET status=?,revision=revision+1,updated_at=?,data=? WHERE id=?",(status,now(),json.dumps(data),work_id))
            row=db.execute("SELECT * FROM reports WHERE id=?",(identifier,)).fetchone()
            self.event(db,row,json.loads(row["data"]),status,user,notes,"assigned" if status=="accepted" else status)
            if action=="blocked":self.emit(db,f"blocked_{work_id}_{revision}",identifier,"A team reported a problem with its assigned visit.",role="management")
        return self.get_report(identifier,user)

    def complete_work(self,identifier,work_id,user,details,photos,digest):
        if user["role"]!="ecology":raise ValueError("Only the ecology field team can submit work evidence.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            work=db.execute("SELECT * FROM work_items WHERE id=? AND report_id=?",(work_id,identifier)).fetchone()
            if not work or work["team_id"]!=user.get("team_id"):return None
            if not db.execute("SELECT teams.id FROM teams JOIN users ON users.team_id=teams.id WHERE teams.id=? AND teams.role='ecology' AND teams.active=1 AND users.id=? AND users.role='ecology' AND users.active=1",(work["team_id"],user["id"])).fetchone():return None
            data=json.loads(work["data"])
            previous=next((item for item in data["completions"] if item["request_key"]==details["request_key"]),None)
            if previous:
                if previous["digest"]!=digest:conflict("This evidence submission key was already used for different content.")
                return self.get_report(identifier,user)
            if work["revision"]!=details["revision"] or work["status"] not in {"accepted","in_progress","correction_requested","blocked"}:conflict("This visit changed. Refresh it before submitting evidence.")
            require_inspection_day(data)
            if data.get("followup_of") and details.get("observed_on")!=data.get("due_on"):raise ValueError("The visit date must match the scheduled inspection date.")
            if data.get('inspection') and not data.get('followup_of') and not data.get('inspections'):raise ValueError('Record the inspection result before submitting restoration evidence.')
            kind=data["work_type"];stage=details["stage"]
            if kind not in {"restoration","inspection","removal","replanting"}:raise ValueError("This historical visit is read-only. Ask management for a new assignment.")
            if kind=="inspection" and not data.get("followup_of") and (not details.get("suggested_species") or not details.get("recommended_action")):raise ValueError("Record the inspected species and recommended next action.")
            if data.get("followup_of"):
                if details.get("regrowth") not in {"yes","no","unknown"} or details.get("replacement_condition") not in {"healthy","struggling","dead","unable"} or details.get("other_invasive") not in {"yes","no"}:
                    raise ValueError("Record invasive regrowth, replacement condition and other suspected plants.")
                if details.get("other_invasive")=="yes":
                    from map_bounds import in_elmina
                    if len(photos)<2 or not in_elmina(details.get("finding_latitude"),details.get("finding_longitude")):
                        raise ValueError("Add a photo and an Elmina map pin for the suspected plant.")
            if kind=="inspection" and details.get("recommended_action")=="removal" and not details.get("removal_recommendation"):raise ValueError("Describe the recommended removal plan for management review.")
            if kind=="inspection" and details.get("recommended_action")=="replanting" and not details.get("replacement_recommendation"):raise ValueError("Describe the recommended replacement planting for management review.")
            if kind=="removal" and stage!="removal" or kind=="replanting" and stage!="replanting" or kind=="removal_replanting" and stage not in {"removal","both"} or kind in {"inspection","monitoring","follow_up"} and stage!="observation":raise ValueError("Choose the evidence stage for this visit.")
            if kind=="restoration":
                if stage not in {"removal","replanting","both"}:raise ValueError("Record removal and replanting evidence for this restoration job.")
                if stage=="both" and len(photos)!=2:raise ValueError("Add a removal photo and a replanting photo.")
                if stage=="removal" and not details.get("planting_pending_reason"):raise ValueError("Explain why replanting is pending.")
                if stage=="replanting":
                    prior=next((item for item in reversed(data["completions"]) if item.get("removal_complete") and item.get("removed_on") and item.get("photo_ids")),None)
                    if not prior:raise ValueError("Record removal evidence before finishing replanting.")
                    if details.get("planted_on") and details["planted_on"]<prior["removed_on"]:raise ValueError("Planting cannot precede the recorded removal.")
            if stage in {"removal","both"} and (not details.get("removed_on") or not details.get("removal_complete")):raise ValueError("Confirm the removal date and completion.")
            if stage in {"replanting","both"}:
                if not details.get("planted_on") or not details.get("planted_species") or (details.get("quantity") or 0)<1:raise ValueError("Record the planted species, quantity and date.")
                if details["planted_species"].strip().casefold()!=data.get("replacement_species","").strip().casefold():raise ValueError("Use the management-approved replacement species, or report a problem to request a changed plan.")
            if kind=="replanting" and data.get("previous_work_id"):
                earlier=db.execute("SELECT data FROM work_items WHERE id=? AND report_id=?",(data["previous_work_id"],identifier)).fetchone()
                removed_on=json.loads(earlier[0])["completions"][-1].get("removed_on") if earlier else None
                if removed_on and details.get("planted_on") and details["planted_on"]<removed_on:raise ValueError("Planting cannot precede the approved removal visit.")
            if kind=="follow_up" and details.get("regrowth") is None:raise ValueError("Record whether invasive regrowth was observed.")
            item={**details,"digest":digest,"submitted_at":now(),"submitted_by":user["display_name"],"photo_ids":[]}
            for mime,content in photos:
                photo_id=uuid4().hex;item["photo_ids"].append(photo_id)
                db.execute("INSERT INTO photos(id,report_id,kind,mime,content,work_id) VALUES (?,?,?,?,?,?)",(photo_id,identifier,"work_evidence",mime,content,work_id))
            data["completions"].append(item);data["verification"]=None
            partial=kind=="restoration" and stage=="removal"
            state="in_progress" if partial else "awaiting_verification"
            db.execute("UPDATE work_items SET status=?,revision=revision+1,updated_at=?,data=? WHERE id=?",(state,now(),json.dumps(data),work_id))
            row=db.execute("SELECT * FROM reports WHERE id=?",(identifier,)).fetchone()
            self.event(db,row,json.loads(row["data"]),"removal_recorded" if partial else "evidence_submitted",user,details["notes"],state)
            self.emit(db,f"evidence_{work_id}_{details['request_key']}",identifier,"Removal recorded; replanting remains pending." if partial else "Job evidence is ready for management review.",role="management")
        return self.get_report(identifier,user)

    def verify_work(self,identifier,work_id,user,details):
        if user["role"]!="management":raise ValueError("Only management can verify field work.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            work=db.execute("SELECT * FROM work_items WHERE id=? AND report_id=?",(work_id,identifier)).fetchone()
            if not work:return None
            if work["revision"]!=details["revision"] or work["status"]!="awaiting_verification":conflict("This visit is no longer awaiting this verification. Refresh it.")
            data=json.loads(work["data"])
            if data.get("work_type") not in {"restoration","inspection","removal","replanting"}:raise ValueError("This historical visit is read-only. Cancel it and create a new assignment.")
            if not data.get("completions"):raise ValueError("This visit has no evidence to review.")
            row=db.execute("SELECT * FROM reports WHERE id=?",(identifier,)).fetchone()
            if data.get("work_type")=="restoration":
                if details.get("next_plan") or details.get("no_followup_reason"):raise ValueError("Completed restoration requires its linked follow-up inspection.")
                if details["decision"]=="accept":
                    last=data["completions"][-1]
                    removed=any(item.get("removal_complete") and item.get("removed_on") and item.get("photo_ids") for item in data["completions"])
                    if not removed or last.get("stage") not in {"both","replanting"} or not all(last.get(key) for key in ("planted_on","planted_species","quantity","photo_ids")):
                        raise ValueError("Removal and replanting evidence are required before closing restoration.")
            if details['decision']=='accept' and data.get('inspection') and not data.get('followup_of') and (not data.get('inspections') or any(item.get('review_status')!='reviewed' for item in data.get('inspections',[]))):
                raise ValueError('Review the inspection results before closing this job.')
            if details['decision']=='accept' and data.get('followup_of') and not details.get('next_plan'):
                last=data['completions'][-1]
                if last.get('regrowth')!='no' or last.get('replacement_condition')!='healthy' or last.get('other_invasive')!='no':
                    raise ValueError('Assign a corrective or repeat inspection plan before closing findings that need further action.')
            next_plan=details.get("next_plan")
            if next_plan and next_plan["revision"]!=row["revision"]:conflict("This report changed. Refresh before approving the next plan.")
            if next_plan and next_plan.get("decision")!="assign":raise ValueError("Choose assignment for the next plan.")
            decision=details["decision"]
            status="correction_requested" if decision=="corrections" else "verified"
            data["verification"]={**details,"verified_by":user["display_name"],"verified_at":now()}
            data["history"].append({"at":now(),"action":status,"by":user["display_name"],"notes":details["notes"]})
            db.execute("UPDATE work_items SET status=?,revision=revision+1,updated_at=?,data=? WHERE id=?",(status,now(),json.dumps(data),work_id))
            report_data=json.loads(row["data"])
            next_team=work["team_id"]
            if decision=="corrections":
                parent="assigned"
                self.emit(db,f"correction_{work_id}_{work['revision']}",identifier,"Management requested changes to your visit evidence.",team_id=work["team_id"])
            elif decision=="reopen":parent="submitted"
            elif not next_plan and data['work_type'] in {'restoration','replanting'} and data['completions'][-1].get('planted_on'):
                last=data['completions'][-1]
                due=details.get('next_visit_on') or (date.fromisoformat(last['planted_on'])+timedelta(days=14)).isoformat()
                if date.fromisoformat(due)<date.fromisoformat(last['planted_on']):raise ValueError('Follow-up cannot precede replanting.')
                point={key:report_data.get(key) for key in ('latitude','longitude','location_mode','map_id','demo_pin')}
                plan={key:data.get(key,'') for key in ('confirmed_species','confirmed_invasive','replacement_species','replanting_instructions')}
                plan.update({'work_type':'inspection','due_on':due,'priority':data.get('priority','normal'),
                    'notes':'Inspect the restored location for invasive regrowth and check replacement planting. Report findings and photographs to management; removal is not authorised by this inspection.',
                    'previous_work_id':work_id,'followup_of':work_id,
                    'restoration_snapshot':{'planted_on':last['planted_on'],'planted_species':last['planted_species'],'quantity':last['quantity'],
                        'completions':data['completions'],'point':point,'inspection':data.get('inspection')}})
                self.new_work(db,identifier,work['team_id'],plan,user)
                report_data['restoration_approved_followup_pending']=True
                parent='follow_up'
            elif next_plan:
                plan={**next_plan,"previous_work_id":work_id}
                if data.get("followup_of") and plan["work_type"]=="inspection":
                    plan.update({"followup_of":data["followup_of"],"restoration_snapshot":data.get("restoration_snapshot")})
                next_team=plan["assigned_team_id"]
                self.new_work(db,identifier,next_team,plan,user)
                team=db.execute("SELECT name FROM teams WHERE id=?",(next_team,)).fetchone()
                report_data["review"]={**plan,"assigned_team_name":team[0],"reviewer_name":user["display_name"],"reviewed_at":now()}
                parent="assigned"
            elif details.get("next_visit_on"):
                # Compatibility for older clients: create only an explicit approved type.
                kind="replanting" if data["work_type"]=="removal" else "inspection"
                plan={key:data.get(key,"") for key in ("confirmed_species","confirmed_invasive","removal_instructions","replacement_species","replanting_instructions")}
                if kind=="replanting" and not all((plan["replacement_species"],plan["replanting_instructions"])):raise ValueError("Approve replacement species and planting instructions in the next plan.")
                plan.update({"work_type":kind,"due_on":details["next_visit_on"],"priority":data.get("priority","normal"),"notes":details["notes"],"previous_work_id":work_id})
                next_team=details.get("assigned_team_id") or work["team_id"]
                self.new_work(db,identifier,next_team,plan,user)
                parent="assigned"
            else:parent="completed"
            if parent=="completed":report_data.pop("restoration_approved_followup_pending",None)
            if decision!="corrections":
                self.emit(db,f"verified_{work_id}_{work['revision']}",identifier,"Management approved your evidence. "+("This case is complete." if parent=="completed" else "Check the next instructions."),team_id=work["team_id"])
            self.event(db,row,report_data,"verification_"+decision,user,details["notes"],parent,next_team)
        return self.get_report(identifier,user)

    def add_information(self,*args,**kwargs):
        result=super().add_information(*args,**kwargs)
        if result:
            with self.connect() as db:self.emit(db,f"information_{result['id']}_{result['revision']}",result["id"],"Additional sighting evidence needs review.",role="management")
        return result

    def notifications(self,user):
        with self.connect() as db:
            for work in db.execute("SELECT * FROM work_items WHERE status NOT IN ('verified','cancelled','awaiting_verification')").fetchall():
                data=json.loads(work["data"])
                if data.get("due_on") and data["due_on"]<field_today().isoformat():
                    for audience in ("management","team"):
                        self.emit(db,"overdue_"+work["id"]+audience,work["report_id"],"A field visit is overdue.",role="management" if audience=="management" else None,team_id=work["team_id"] if audience=="team" else None)
            rows=db.execute("""SELECT n.*,r.read_at FROM notices n LEFT JOIN notice_reads r ON r.notice_id=n.id AND r.user_id=?
                WHERE n.role=? OR n.user_id=? OR (n.team_id IS NOT NULL AND n.team_id=?) ORDER BY n.created_at DESC LIMIT 100""",(user["id"],user["role"],user["id"],user.get("team_id"))).fetchall()
        return [dict(row) for row in rows if not row["report_id"] or self.get_report(row["report_id"],user)]

    def mark_notice(self,identifier,user):
        if identifier not in {item["id"] for item in self.notifications(user)}:return False
        with self.connect() as db:db.execute("INSERT OR IGNORE INTO notice_reads VALUES (?,?,?)",(identifier,user["id"],now()))
        return True

    def catalog(self):
        with self.connect() as db:
            return {"sites":[dict(row) for row in db.execute("SELECT * FROM sites WHERE active=1 ORDER BY name")],"blocks":[dict(row) for row in db.execute("SELECT * FROM blocks WHERE active=1 ORDER BY name")]}

    def duplicate_candidates(self,identifier,user):
        report=self.get_report(identifier,user)
        if not report:return []
        return [{"id":item["id"],"reference":item["reference"],"site":item["site"],"landmark":item["landmark"]} for item in self.list_reports(user) if item["id"]!=identifier and item["status"]!="duplicate" and item["site"].casefold().strip()==report["site"].casefold().strip()]

    def backup_database(self):
        folder=self.directory/"backups";folder.mkdir(exist_ok=True)
        target=folder/("backup-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-")+secrets.token_hex(3)+".sqlite3")
        with closing(sqlite3.connect(self.database)) as source,closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
            if destination.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("Backup integrity check failed.")
        return {"name":target.name,"bytes":target.stat().st_size,"created_at":now()}

    def audit(self,actor,action,target):
        with self.connect() as db:db.execute("INSERT INTO admin_audit VALUES (?,?,?,?,?)",(uuid4().hex,actor["id"],action,target,now()))

    def change_password(self,user,current,new):
        from records import password_hash
        import hmac
        if len(new)<10:raise ValueError("Use at least 10 characters.")
        with self.connect() as db:
            row=db.execute("SELECT * FROM users WHERE id=?",(user["id"],)).fetchone()
            if not hmac.compare_digest(password_hash(current,row["salt"]),row["password_hash"]):raise ValueError("Current password is incorrect.")
            salt=secrets.token_hex(16)
            db.execute("UPDATE users SET salt=?,password_hash=?,must_change_password=0 WHERE id=?",(salt,password_hash(new,salt),user["id"]))
            db.execute("DELETE FROM sessions WHERE user_id=?",(user["id"],))
        self.audit(user,"password_changed",user["id"])

    def admin_users(self):
        with self.connect() as db:
            return [{**self.public_user(row),"active":bool(row["active"])} for row in db.execute("SELECT * FROM users ORDER BY display_name")]

    def reset_user(self,actor,identifier):
        from records import password_hash
        temporary=secrets.token_urlsafe(15);salt=secrets.token_hex(16)
        with self.connect() as db:
            if not db.execute("SELECT id FROM users WHERE id=?",(identifier,)).fetchone():return None
            db.execute("UPDATE users SET salt=?,password_hash=?,must_change_password=1 WHERE id=?",(salt,password_hash(temporary,salt),identifier))
            db.execute("DELETE FROM sessions WHERE user_id=?",(identifier,))
        self.audit(actor,"temporary_password_issued",identifier)
        return temporary

    def set_user_active(self,actor,identifier,active):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            target=db.execute("SELECT * FROM users WHERE id=?",(identifier,)).fetchone()
            if not target:return False
            if not active and target["role"]=="management" and db.execute("SELECT COUNT(*) FROM users WHERE active=1 AND role='management'").fetchone()[0]<=1:raise ValueError("Keep at least one active management account.")
            if not active and target["team_id"] and db.execute("SELECT COUNT(*) FROM users WHERE active=1 AND role=? AND team_id=? AND id!=?",(target["role"],target["team_id"],identifier)).fetchone()[0]==0 and db.execute("SELECT id FROM work_items WHERE team_id=? AND status NOT IN ('verified','cancelled')",(target["team_id"],)).fetchone():raise ValueError("Reassign or cancel this team's active work before disabling its last member.")
            db.execute("UPDATE users SET active=? WHERE id=?",(int(active),identifier))
            if not active:db.execute("DELETE FROM sessions WHERE user_id=?",(identifier,))
        self.audit(actor,"user_enabled" if active else "user_disabled",identifier)
        return True

    def validate_location(self,details):
        from fastapi import HTTPException
        with self.connect() as db:
            site_id,block_id=details.get("site_id"),details.get("block_id")
            if block_id and not site_id:raise HTTPException(422,"Choose the site for this block.")
            if site_id:
                site=db.execute("SELECT * FROM sites WHERE id=? AND active=1",(site_id,)).fetchone()
                if not site:raise HTTPException(422,"Choose an active site.")
                details["site"]=site["name"]
            if block_id:
                block=db.execute("SELECT * FROM blocks WHERE id=? AND site_id=? AND active=1",(block_id,site_id)).fetchone()
                if not block:raise HTTPException(422,"Choose a block belonging to this site.")
                details["block_name"]=block["name"]

    def add_catalog(self,actor,kind,name,site_id=None,role="ecology"):
        if kind not in {"teams","sites","blocks"}:raise ValueError("Unknown list.")
        name=name.strip()
        if not name or len(name)>100:raise ValueError("Use a name between 1 and 100 characters.")
        identifier=uuid4().hex
        try:
            with self.connect() as db:
                if kind=="blocks":
                    if not db.execute("SELECT id FROM sites WHERE id=? AND active=1",(site_id,)).fetchone():raise ValueError("Choose an active site.")
                    db.execute("INSERT INTO blocks(id,site_id,name) VALUES (?,?,?)",(identifier,site_id,name))
                elif kind=="teams":
                    if role not in {"ground","ecology"}:raise ValueError("Choose a ground or ecology team.")
                    db.execute("INSERT INTO teams(id,name,role) VALUES (?,?,?)",(identifier,name,role))
                else:db.execute(f"INSERT INTO {kind}(id,name) VALUES (?,?)",(identifier,name))
        except sqlite3.IntegrityError as error:raise ValueError("That name already exists in this list.") from error
        self.audit(actor,kind+"_created",identifier)
        return {"id":identifier,"name":name,**({"role":role} if kind=="teams" else {})}

    def set_catalog_active(self,actor,kind,identifier,active):
        if kind not in {"teams","sites","blocks"}:raise ValueError("Unknown list.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute(f"SELECT id FROM {kind} WHERE id=?",(identifier,)).fetchone():return False
            if kind=="teams" and not active and db.execute("SELECT id FROM work_items WHERE team_id=? AND status NOT IN ('verified','cancelled')",(identifier,)).fetchone():raise ValueError("Reassign or cancel the team's active visits first.")
            db.execute(f"UPDATE {kind} SET active=? WHERE id=?",(int(active),identifier))
        self.audit(actor,kind+("_enabled" if active else "_disabled"),identifier)
        return True
