#!/usr/bin/env python3
"""ALT v0.2 importer: reviewable, atomic, deterministic CSV/JSON ingestion.
BareBones Projects. No auto-publication; imports default to draft.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3

MAX_IMPORT_BYTES=32*1024*1024
ALLOWED_KINDS={'star','planet','moon','system','location','hex','route','character','faction','item','lore'}
ID_RE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')
UNIT_SET={'ly','pc','au','km','m'}
FRAME_RE=re.compile(r'^[A-Za-z0-9_.:-]{1,100}$')

def read_records(path):
    path=Path(path)
    if path.suffix.lower() not in {'.csv','.json'}:raise ValueError('Input must be CSV or JSON')
    if path.stat().st_size>MAX_IMPORT_BYTES:raise ValueError('Input exceeds 32 MiB')
    raw=path.read_bytes();file_sha=hashlib.sha256(raw).hexdigest()
    if path.suffix.lower()=='.csv':
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if not reader.fieldnames or not {'id','kind','name'}.issubset(reader.fieldnames):
            raise ValueError('CSV requires id,kind,name columns')
        entries=list(reader)
    else:
        obj=json.loads(raw)
        entries=obj.get('entries') if isinstance(obj,dict) else obj
        if not isinstance(entries,list):raise ValueError('JSON needs an entries array')
    if len(entries)>50000:raise ValueError('Too many records')
    return entries,file_sha,path.suffix.lower().lstrip('.')

def normalize(rows,source_id,source_revision,frame,unit,visibility):
    if not ID_RE.fullmatch(source_id) or not source_revision or len(source_revision)>128:
        raise ValueError('Invalid source metadata')
    if frame and not FRAME_RE.fullmatch(frame):raise ValueError('Invalid coordinate frame')
    if unit and unit not in UNIT_SET:raise ValueError('Invalid coordinate unit')
    if visibility not in {'draft','restricted'}:raise ValueError('Import visibility must be draft or restricted; publish separately after review')
    cleaned=[];seen=set()
    for idx,raw in enumerate(rows,1):
        if not isinstance(raw,dict):raise ValueError(f'Row {idx} not an object')
        entity_id=raw.get('id');kind=raw.get('kind');name=raw.get('name')
        if not isinstance(entity_id,str) or not ID_RE.fullmatch(entity_id) or entity_id in seen:
            raise ValueError(f'Invalid or duplicate ID at row {idx}')
        if kind not in ALLOWED_KINDS or not isinstance(name,str) or not (1<=len(name)<=200):
            raise ValueError(f'Invalid kind/name at row {idx}')
        seen.add(entity_id)
        parent=raw.get('parent_id') or None
        if parent is not None and (not isinstance(parent,str) or not ID_RE.fullmatch(parent)):
            raise ValueError(f'Invalid parent at row {idx}')
        extra=raw.get('data',{})
        if isinstance(extra,str):
            try:extra=json.loads(extra) if extra.strip() else {}
            except json.JSONDecodeError:raise ValueError(f'Invalid data JSON at row {idx}')
        if not isinstance(extra,dict):raise ValueError(f'Invalid data at row {idx}')
        if kind in {'star','planet','moon','system'}:
            # Source frame/units are explicit, never infer from viewer layout positions.
            extra=dict(extra)
            if frame:extra['coordinate_frame']=frame
            if unit:extra['coordinate_unit']=unit
        canonical=json.dumps(extra,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        if len(canonical)>100000:raise ValueError(f'Oversize data at row {idx}')
        record_id=raw.get('source_record_id') or entity_id
        if not isinstance(record_id,str) or not ID_RE.fullmatch(record_id):raise ValueError(f'Bad source record ID at row {idx}')
        record_sha=hashlib.sha256(json.dumps(raw,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
        cleaned.append((entity_id,kind,name,parent,visibility,canonical,source_id,source_revision,record_id,record_sha,frame,unit))
    return cleaned

def import_records(connection,records,source_id,source_revision,file_sha,fmt,apply=False,conflict='reject'):
    if conflict not in ('reject','skip','update'):raise ValueError('Invalid collision policy')
    if not ID_RE.fullmatch(source_id):raise ValueError('Invalid source ID')
    ids=[r[0] for r in records]
    known={row[0]:row[1] for row in connection.execute('SELECT entity_id,source_id FROM canon_provenance')}
    present={r[0] for r in connection.execute('SELECT id FROM entities')}
    operations=[];errors=[]
    for record in records:
        key=record[0]
        if key in present:
            if conflict=='reject':errors.append(key);continue
            if conflict=='skip':operations.append(('skip',record));continue
            if known.get(key)!=source_id:
                errors.append(key);continue
            operations.append(('update',record))
        else:operations.append(('insert',record))
    if errors:raise ValueError('Collision or source ownership conflict: '+','.join(errors[:10]))
    counts={k:sum(op==k for op,_ in operations) for k in ('insert','update','skip')}
    report={'source_id':source_id,'source_revision':source_revision,'sha256':file_sha,'dry_run':not apply,'total':len(records),'counts':counts}
    if not apply:return report
    batch_id=hashlib.sha256((source_id+'\0'+source_revision+'\0'+file_sha).encode()).hexdigest()
    with connection:
        for operation,record in operations:
            if operation=='skip':continue
            eid,kind,name,parent,visibility,data,src,rev,rid,hash_value,frame,unit=record
            if operation=='insert':
                connection.execute('INSERT INTO entities(id,kind,name,parent_id,visibility,data_json) VALUES(?,?,?,?,?,?)',(eid,kind,name,parent,visibility,data))
            else:
                connection.execute("UPDATE entities SET kind=?,name=?,parent_id=?,visibility=?,data_json=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                   (kind,name,parent,visibility,data,eid))
            connection.execute('INSERT INTO canon_provenance(entity_id,source_id,source_revision,source_record_id,source_sha256,coordinate_frame,coordinate_unit) VALUES(?,?,?,?,?,?,?) ON CONFLICT(entity_id) DO UPDATE SET source_revision=excluded.source_revision,source_record_id=excluded.source_record_id,source_sha256=excluded.source_sha256,coordinate_frame=excluded.coordinate_frame,coordinate_unit=excluded.coordinate_unit,imported_at=CURRENT_TIMESTAMP',(eid,src,rev,rid,hash_value,frame,unit))
        connection.execute('INSERT OR IGNORE INTO ingest_sources(source_id,repo,last_revision) VALUES(?,?,?)',(source_id,source_id,source_revision))
        connection.execute("UPDATE ingest_sources SET last_revision=?,updated_at=CURRENT_TIMESTAMP WHERE source_id=?",(source_revision,source_id))
        connection.execute('INSERT OR IGNORE INTO ingest_batches(batch_id,source_id,file_sha256,format,row_count,imported_count,skipped_count) VALUES(?,?,?,?,?,?,?)',(batch_id,source_id,file_sha,fmt,len(records),counts['insert']+counts['update'],counts['skip']))
    report['dry_run']=False
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('--db',required=True,help='Existing initialized SQLite file')
    p.add_argument('--source',required=True,help='Source repository ID')
    p.add_argument('--revision',required=True)
    p.add_argument('--frame')
    p.add_argument('--unit',choices=sorted(UNIT_SET))
    p.add_argument('--visibility',choices=['draft','restricted'],default='draft')
    p.add_argument('--conflict',choices=['reject','skip','update'],default='reject')
    p.add_argument('--apply',action='store_true',help='Explicitly commit; default dry run')
    args=p.parse_args()
    if not Path(args.db).is_file():p.error('Database must already exist; run server.py init')
    entries,sha,fmt=read_records(args.input)
    rows=normalize(entries,args.source,args.revision,args.frame,args.unit,args.visibility)
    db=sqlite3.connect(args.db)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        report=import_records(db,rows,args.source,args.revision,sha,fmt,args.apply,args.conflict)
        print(json.dumps(report,indent=2))
    finally:db.close()
if __name__=='__main__':main()
