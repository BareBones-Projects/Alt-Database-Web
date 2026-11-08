#!/usr/bin/env python3
"""BareBones Projects: transform alt-star-map-db astronomical CSV into reviewable ALT records.
Do not infer authoritative status from a map fixture. No imports are published automatically.
"""
import argparse
import csv
import json
import re
from pathlib import Path

def make_id(name,kind):
    slug=re.sub(r'[^A-Z0-9]+','-',name.upper()).strip('-')
    return f'ALT-{kind.upper()}-{slug}'[:128]

def convert(source):
    entries=[];seen=set()
    with Path(source).open(encoding='utf-8-sig',newline='') as stream:
        for number,row in enumerate(csv.DictReader(stream),start=2):
            name=(row.get('name') or '').strip()
            kind=(row.get('type') or '').strip().lower()
            if not name or kind not in {'star','planet','moon'}:raise ValueError(f'Invalid type or name on line {number}')
            key=make_id(name,kind)
            if key in seen:raise ValueError(f'Duplicate canonical candidate {key} on line {number}')
            seen.add(key)
            coords={}
            for axis in ('x_ly_local','y_ly_local','z_ly_local'):
                value=(row.get(axis) or '').strip()
                if value:coords[axis]=float(value)
            data={'source_parent_name':row.get('parent') or None,'coordinates_local_ly':coords,
                  'body_class':row.get('body_class') or None,'classification_note':row.get('notes') or None,
                  'canonical_status':'pending_review','coordinate_frame':'ALT-LOCAL-SOL','coordinate_unit':'ly'}
            entries.append({'id':key,'kind':kind,'name':name,'source_record_id':key,'data':data})
    return {'schema':'ALT-INGEST-v0.2','entries':entries}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('csv');p.add_argument('--output',required=True);args=p.parse_args()
    data=convert(args.csv)
    Path(args.output).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(len(data['entries']),'draft astronomical candidates written')
