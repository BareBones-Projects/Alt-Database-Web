#!/usr/bin/env python3
"""ALT Database v0.1: stdlib SQLite canonical read API and admin-only editor.
BareBones Projects. Deploy behind HTTPS; do not expose development HTTP publicly.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, unquote

ROOT = Path(__file__).resolve().parent.parent
DATABASE = Path(os.getenv("ALT_DB_PATH", str(ROOT / "runtime" / "alt.sqlite3")))
MEDIA_DIR = Path(os.getenv("ALT_MEDIA_DIR", str(ROOT / "runtime" / "media")))
MAX_BODY = 12 * 1024 * 1024
KINDS = {"star","planet","moon","system","location","hex","route","character","faction","item","lore"}
VISIBILITIES = {"draft","public","restricted"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
ALLOWED_MIME = {"image/png","image/jpeg","image/webp","image/gif","video/mp4","video/webm","text/plain","text/csv","application/json","application/pdf"}
FILE_SIGS = {"image/png": bytes.fromhex("89504e470d0a1a0a"), "image/jpeg":bytes.fromhex("ffd8ff"),"image/webp":b"RIFF", "image/gif":b"GIF8", "application/pdf":b"%PDF"}
SESSION_TTL = 8 * 60 * 60
CELL_PATTERN = re.compile(r"^ALT-HX-L([0-4])-Q(-?\d+)-R(-?\d+)-K(-?\d+)$")

def connect():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE,timeout=15)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    return db

def init_db():
    with connect() as db:
        db.executescript((ROOT / "backend" / "schema.sql").read_text())
        db.executescript((ROOT / "backend" / "sync_schema.sql").read_text())

def digest_password(password,salt,iterations=310000):
    return hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),iterations).hex()

def bootstrap_admin(username,password):
    if not username or len(password)<14: raise ValueError("Username required; password must be at least 14 characters")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}",username):raise ValueError("Invalid admin username")
    salt=secrets.token_hex(16)
    with connect() as db:
        db.execute("INSERT INTO admins(username,salt,password_hash,iterations) VALUES (?,?,?,?)",
                   (username,salt,digest_password(password,salt),310000))

def public_entity(row):
    return {"id":row["id"],"kind":row["kind"],"name":row["name"],"parent_id":row["parent_id"],
            "revision":row["revision"],"visibility":row["visibility"],"data":json.loads(row["data_json"])}

class Handler(BaseHTTPRequestHandler):
    server_version="ALTDB/0.1"
    def headers_common(self,mime,length):
        self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(length))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("X-Frame-Options","DENY")
        self.send_header("Content-Security-Policy","default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
    def public_cors(self):
        origin=self.headers.get("Origin","")
        allowed={x.strip() for x in os.getenv("ALT_PUBLIC_ORIGINS","").split(",") if x.strip()}
        path=urlsplit(self.path).path
        if origin in allowed and (path.startswith("/api/v1/") or path.startswith("/v1/")) and not path.startswith("/api/v1/admin/"):
            self.send_header("Access-Control-Allow-Origin",origin)
            self.send_header("Vary","Origin")
    def send_data(self,status,data,extra=None):
        raw=json.dumps(data,ensure_ascii=False,separators=(",",":")).encode()
        self.send_response(status)
        self.headers_common("application/json; charset=utf-8",len(raw))
        self.public_cors()
        for k,v in (extra or {}).items():self.send_header(k,v)
        self.end_headers();self.wfile.write(raw)
    def send_page(self,path,mime):
        payload=path.read_bytes()
        self.send_response(200);self.headers_common(mime,len(payload));self.end_headers();self.wfile.write(payload)
    def body(self):
        try:n=int(self.headers.get("Content-Length","0"))
        except ValueError:raise ValueError("INVALID_LENGTH")
        if n<=0 or n>MAX_BODY:raise ValueError("BODY_SIZE")
        try: data=json.loads(self.rfile.read(n))
        except (ValueError,UnicodeDecodeError):raise ValueError("INVALID_JSON")
        if not isinstance(data,dict):raise ValueError("OBJECT_REQUIRED")
        return data
    def session(self):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get("Cookie",""))
        except Exception:return None
        value=cookie.get("altdb_session")
        if not value:return None
        token=value.value
        if not re.fullmatch(r"[a-f0-9]{64}",token):return None
        with connect() as db:
            row=db.execute("SELECT username,csrf_token FROM sessions WHERE token_hash=? AND expires_at>?",(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
        return row
    def secure_cookie(self):
        # Set ALT_COOKIE_SECURE=0 ONLY when testing on localhost HTTP.
        return os.getenv("ALT_COOKIE_SECURE","1")!="0"
    def require_admin(self,write=False):
        row=self.session()
        if row is None:
            self.send_data(401,{"error":"ADMIN_LOGIN_REQUIRED"});return None
        if write:
            origin=self.headers.get("Origin")
            host=self.headers.get("Host","")
            if origin and urlsplit(origin).netloc!=host:
                self.send_data(403,{"error":"ORIGIN_REJECTED"});return None
            if not hmac.compare_digest(self.headers.get("X-CSRF-Token",""),row["csrf_token"]):
                self.send_data(403,{"error":"CSRF_REJECTED"});return None
        return row
    def do_GET(self):
        path=unquote(urlsplit(self.path).path)
        if path=="/admin": 
            if not self.session():return self.send_data(401,{"error":"ADMIN_LOGIN_REQUIRED","login":"/login"})
            return self.send_page(ROOT/"admin"/"dashboard.html","text/html; charset=utf-8")
        if path=="/login":return self.send_page(ROOT/"admin"/"login.html","text/html; charset=utf-8")
        if path=="/login.js":return self.send_page(ROOT/"admin"/"login.js","application/javascript; charset=utf-8")
        if path=="/admin/app.js":
            if not self.session():return self.send_data(401,{"error":"ADMIN_LOGIN_REQUIRED"})
            return self.send_page(ROOT/"admin"/"app.js","application/javascript; charset=utf-8")
        if path=="/api/v1/admin/session":
            s=self.require_admin()
            if s:return self.send_data(200,{"username":s["username"],"csrf_token":s["csrf_token"]})
            return
        if path in ("/api/v1/health","/v1/health"):return self.send_data(200,{"status":"ok","api_version":"v1","storage":"sqlite"})
        if path=="/api/v1/changes":
            params=parse_qs(urlsplit(self.path).query)
            try:
                since=int(params.get("since",["0"])[0])
                if since<0:raise ValueError()
            except (ValueError,TypeError):return self.send_data(400,{"error":"INVALID_REVISION"})
            with connect() as db:
                maximum=db.execute("SELECT COALESCE(MAX(sequence),0) FROM canon_changes").fetchone()[0]
                changes=db.execute("""SELECT c.sequence,c.entity_id,c.change_kind,c.visibility
                   FROM canon_changes c
                   WHERE c.sequence>? AND (c.visibility='public' OR
                   EXISTS (SELECT 1 FROM canon_changes previous WHERE previous.entity_id=c.entity_id
                           AND previous.sequence<c.sequence AND previous.visibility='public'))
                   ORDER BY c.sequence LIMIT 501""",(since,)).fetchall()
                changed_objects=[];withdrawn=[];changed_cells=set()
                for c in changes[:500]:
                    if c["visibility"]=="public":
                        changed_objects.append(c["entity_id"])
                        row=db.execute("SELECT data_json,kind FROM entities WHERE id=? AND visibility='public'",(c["entity_id"],)).fetchone()
                        if row:
                            details=json.loads(row["data_json"])
                            if row["kind"]=="hex":changed_cells.add(c["entity_id"])
                            cell=details.get("cell_id")
                            if isinstance(cell,str) and CELL_PATTERN.fullmatch(cell):changed_cells.add(cell)
                    else:withdrawn.append(c["entity_id"])
            return self.send_data(200,{"revision":maximum,"next_since":changes[499]["sequence"] if len(changes)>500 else maximum,
                "has_more":len(changes)>500,"changed_objects":sorted(set(changed_objects)),
                "withdrawn_objects":sorted(set(withdrawn)),"changed_cells":sorted(changed_cells)})
        if path.startswith("/api/v1/hex-cells/") and path.endswith("/contents"):
            cell_id=path[len("/api/v1/hex-cells/"):-len("/contents")].strip("/")
            if not CELL_PATTERN.fullmatch(cell_id):return self.send_data(400,{"error":"INVALID_CELL_ID"})
            with connect() as db:
                matched=[]
                for row in db.execute("SELECT id,data_json FROM entities WHERE visibility='public' AND kind IN ('hex','location','route')"):
                    details=json.loads(row["data_json"])
                    if row["id"]==cell_id or details.get("cell_id")==cell_id:matched.append((row["id"],details))
                objects=[key for key,details in matched if details.get("entity_type")!="route"]
                routes=[key for key,details in matched if details.get("entity_type")=="route"]
                latest=db.execute("SELECT COALESCE(MAX(sequence),0) FROM canon_changes").fetchone()[0]
            return self.send_data(200,{"cell_id":cell_id,"revision":latest,"objects":objects,"routes":routes,
                "level":int(CELL_PATTERN.fullmatch(cell_id).group(1)),"grid_id":"ALT-HEX-001"})
        if path=="/api/v1/entities":
            q=parse_qs(urlsplit(self.path).query)
            kind=q.get("kind",[""])[0]
            if kind and kind not in KINDS:return self.send_data(400,{"error":"INVALID_KIND"})
            with connect() as db:
                rows=db.execute("SELECT * FROM entities WHERE visibility='public' AND (?='' OR kind=?) ORDER BY id LIMIT 500",(kind,kind)).fetchall()
            return self.send_data(200,{"schema_version":"1","entries":[public_entity(r) for r in rows]})
        if path=="/api/v1/admin/entities":
            if not self.require_admin():return
            with connect() as db:rows=db.execute("SELECT * FROM entities ORDER BY updated_at DESC LIMIT 500").fetchall()
            return self.send_data(200,{"entries":[public_entity(r) for r in rows]})
        if path=="/api/v1/admin/media":
            if not self.require_admin():return
            with connect() as db: rows=db.execute("SELECT id,entity_id,filename,mime,bytes,sha256,visibility FROM media ORDER BY created_at DESC LIMIT 500").fetchall()
            return self.send_data(200,{"entries":[dict(r) for r in rows]})
        if path=="/api/v1/media":
            with connect() as db:rows=db.execute("SELECT id,entity_id,filename,mime,bytes,sha256 FROM media WHERE visibility='public' ORDER BY created_at DESC LIMIT 500").fetchall()
            return self.send_data(200,{"entries":[dict(r) for r in rows]})
        if path.startswith("/api/v1/media/"):
            media_id=path.rsplit("/",1)[-1]
            with connect() as db:row=db.execute("SELECT * FROM media WHERE id=? AND visibility='public'",(media_id,)).fetchone()
            if not row:return self.send_data(404,{"error":"NOT_FOUND"})
            target=MEDIA_DIR/row["storage_path"]
            if not target.is_file():return self.send_data(404,{"error":"MISSING_STORAGE"})
            return self.send_page(target,row["mime"])
        if path=="/api/v1/planets":
            with connect() as db:rows=db.execute("SELECT * FROM entities WHERE kind='planet' AND visibility='public'").fetchall()
            return self.send_data(200,{"schema":"ALT-PLANET-LOCATION-v1","entries":[public_entity(r) for r in rows]})
        if path=="/v1/map/snapshot":
            with connect() as db:rows=db.execute("SELECT * FROM entities WHERE visibility='public' AND kind IN ('star','planet','moon','system','location','hex','route') ORDER BY id LIMIT 500").fetchall()
            return self.send_data(200,{"api_version":"v1","schema_version":"1","revision":max([r["revision"] for r in rows],default=0),"data":{"objects":[public_entity(r) for r in rows]}})
        if path.startswith("/v1/objects/") or path.startswith("/api/v1/objects/"):
            key=path.rsplit("/",1)[-1]
            with connect() as db:row=db.execute("SELECT * FROM entities WHERE id=? AND visibility='public'",(key,)).fetchone()
            return self.send_data(200,public_entity(row)) if row else self.send_data(404,{"error":"NOT_FOUND"})
        if path=="/":return self.send_page(ROOT/"index.html","text/html; charset=utf-8")
        return self.send_data(404,{"error":"NOT_FOUND"})
    def do_POST(self):
        path=urlsplit(self.path).path
        try:data=self.body()
        except ValueError as exc:return self.send_data(400,{"error":str(exc)})
        if path=="/api/v1/admin/login":
            username=data.get("username","");password=data.get("password","")
            if not isinstance(username,str) or not isinstance(password,str):return self.send_data(400,{"error":"INVALID_CREDENTIALS"})
            with connect() as db:row=db.execute("SELECT * FROM admins WHERE username=?",(username,)).fetchone()
            # Same-cost verification for unknown users.
            salt=row["salt"] if row else "0"*32
            rounds=row["iterations"] if row else 310000
            attempted=digest_password(password,salt,rounds)
            expected=row["password_hash"] if row else "0"*64
            if not hmac.compare_digest(attempted,expected):
                time.sleep(0.15)
                return self.send_data(401,{"error":"INVALID_CREDENTIALS"})
            token=secrets.token_hex(32);csrf=secrets.token_hex(32)
            with connect() as db:
                db.execute("INSERT INTO sessions(token_hash,username,expires_at,csrf_token) VALUES (?,?,?,?)",
                           (hashlib.sha256(token.encode()).hexdigest(),username,int(time.time())+SESSION_TTL,csrf))
            flags="; HttpOnly; SameSite=Strict; Path=/; Max-Age="+str(SESSION_TTL)
            if self.secure_cookie():flags+="; Secure"
            return self.send_data(200,{"ok":True}, {"Set-Cookie":"altdb_session="+token+flags})
        if path=="/api/v1/admin/logout":
            row=self.require_admin(write=True)
            if not row:return
            cookie=SimpleCookie();cookie.load(self.headers.get("Cookie",""))
            token=cookie.get("altdb_session")
            if token:
                with connect() as db:db.execute("DELETE FROM sessions WHERE token_hash=?",(hashlib.sha256(token.value.encode()).hexdigest(),))
            return self.send_data(200,{"ok":True},{"Set-Cookie":"altdb_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
        if path=="/api/v1/admin/entities":
            s=self.require_admin(write=True)
            if not s:return
            eid=data.get("id");kind=data.get("kind");name=data.get("name");visibility=data.get("visibility","draft")
            details=data.get("data",{})
            if not isinstance(eid,str) or not ID_PATTERN.fullmatch(eid) or kind not in KINDS or not isinstance(name,str) or not 1<=len(name)<=200 or visibility not in VISIBILITIES or not isinstance(details,dict):
                return self.send_data(422,{"error":"INVALID_ENTITY"})
            parent=data.get("parent_id")
            if parent is not None and (not isinstance(parent,str) or not ID_PATTERN.fullmatch(parent)):return self.send_data(422,{"error":"INVALID_PARENT"})
            serialized=json.dumps(details,ensure_ascii=False)
            if len(serialized)>100000:return self.send_data(413,{"error":"ENTITY_TOO_LARGE"})
            try:
                with connect() as db:
                    db.execute("INSERT INTO entities(id,kind,name,parent_id,visibility,data_json) VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,name=excluded.name,parent_id=excluded.parent_id,visibility=excluded.visibility,data_json=excluded.data_json,revision=entities.revision+1,updated_at=CURRENT_TIMESTAMP",
                               (eid,kind,name,parent,visibility,serialized))
                    db.execute("INSERT INTO audit_log(username,action,target) VALUES (?,?,?)",(s["username"],"upsert_entity",eid))
            except sqlite3.IntegrityError:return self.send_data(409,{"error":"INVALID_PARENT_REFERENCE"})
            return self.send_data(200,{"ok":True,"id":eid})
        if path=="/api/v1/admin/media":
            s=self.require_admin(write=True)
            if not s:return
            media_id=data.get("id");entity_id=data.get("entity_id");mime=data.get("mime");filename=data.get("filename","")
            visibility=data.get("visibility","draft")
            if not isinstance(media_id,str) or not ID_PATTERN.fullmatch(media_id) or mime not in ALLOWED_MIME or visibility not in VISIBILITIES or not isinstance(filename,str) or not 1<=len(filename)<=240:
                return self.send_data(422,{"error":"INVALID_MEDIA"})
            if entity_id is not None and (not isinstance(entity_id,str) or not ID_PATTERN.fullmatch(entity_id)):return self.send_data(422,{"error":"INVALID_ENTITY_ID"})
            try:raw=base64.b64decode(data.get("content_base64",""),validate=True)
            except (ValueError,TypeError):return self.send_data(422,{"error":"INVALID_BASE64"})
            if not raw or len(raw)>8*1024*1024:return self.send_data(413,{"error":"MEDIA_SIZE"})
            if mime in FILE_SIGS and not raw.startswith(FILE_SIGS[mime]):return self.send_data(422,{"error":"SIGNATURE_MISMATCH"})
            if mime=="image/webp" and raw[8:12]!=b"WEBP":return self.send_data(422,{"error":"SIGNATURE_MISMATCH"})
            sha=hashlib.sha256(raw).hexdigest()
            MEDIA_DIR.mkdir(parents=True,exist_ok=True)
            storage=sha+".bin"
            (MEDIA_DIR/storage).write_bytes(raw)
            try:
                with connect() as db:
                    db.execute("INSERT INTO media(id,entity_id,filename,mime,bytes,sha256,storage_path,visibility) VALUES (?,?,?,?,?,?,?,?)",(media_id,entity_id,Path(filename).name,mime,len(raw),sha,storage,visibility))
                    db.execute("INSERT INTO audit_log(username,action,target) VALUES (?,?,?)",(s["username"],"upload_media",media_id))
            except sqlite3.IntegrityError:return self.send_data(409,{"error":"MEDIA_EXISTS_OR_MISSING_ENTITY"})
            return self.send_data(201,{"ok":True,"id":media_id,"sha256":sha})
        return self.send_data(404,{"error":"NOT_FOUND"})

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["serve","init","create-admin"])
    p.add_argument("--host",default="127.0.0.1")
    p.add_argument("--port",type=int,default=8090)
    p.add_argument("--username")
    args=p.parse_args()
    init_db()
    if args.command=="create-admin":
        import getpass
        bootstrap_admin(args.username or input("Admin username: "),getpass.getpass("Admin password: "))
        print("Admin account created")
    elif args.command=="serve":
        with ThreadingHTTPServer((args.host,args.port),Handler) as server:
            print("ALT Database listening on",server.server_address)
            server.serve_forever()
    else:print("Database initialized")
if __name__=="__main__":main()
