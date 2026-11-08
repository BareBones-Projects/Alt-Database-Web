"""BareBones Projects: canonical importer, provenance and change-feed regression."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    instance=importlib.util.module_from_spec(spec);spec.loader.exec_module(instance);return instance
server=module('alt_sync_server','backend/server.py')
imp=module('alt_sync_import','backend/import_canon.py')

class CanonSyncTests(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory()
    self.old=server.DATABASE
    server.DATABASE=Path(self.tmp.name)/'test.sqlite3'
    server.init_db()
 def tearDown(self):
    server.DATABASE=self.old;self.tmp.cleanup()
 def records(self):
    return imp.normalize([
      {'id':'ALT-HX-L0-Q0-R0-K0','kind':'hex','name':'Demo Hex','data':{'cell_id':'ALT-HX-L0-Q0-R0-K0'}},
      {'id':'ALT-LOC-DEMO','kind':'location','name':'Demo Location','data':{'cell_id':'ALT-HX-L0-Q0-R0-K0'}}],
      'test-source','rev1',None,None,'draft')
 def test_dry_run_then_atomic_import_and_provenance(self):
    rows=self.records()
    with server.connect() as db:
      dry=imp.import_records(db,rows,'test-source','rev1','a'*64,'json')
      self.assertTrue(dry['dry_run'])
      self.assertEqual(db.execute('SELECT COUNT(*) FROM entities').fetchone()[0],0)
      done=imp.import_records(db,rows,'test-source','rev1','a'*64,'json',apply=True)
      self.assertEqual(done['counts']['insert'],2)
      self.assertEqual(db.execute('SELECT COUNT(*) FROM canon_provenance').fetchone()[0],2)
      with self.assertRaisesRegex(ValueError,'Collision'):
        imp.import_records(db,rows,'test-source','rev2','b'*64,'json',apply=True)
      self.assertEqual(db.execute('SELECT COUNT(*) FROM entities').fetchone()[0],2)
      updated=imp.import_records(db,rows,'test-source','rev2','b'*64,'json',apply=True,conflict='update')
      self.assertEqual(updated['counts']['update'],2)
      self.assertEqual(db.execute('SELECT revision FROM entities WHERE id=?',('ALT-LOC-DEMO',)).fetchone()[0],2)
 def test_import_rejects_duplicates_and_auto_publication(self):
    source=[{'id':'X','kind':'location','name':'X'}]
    with self.assertRaises(ValueError):imp.normalize(source*2,'source','r1',None,None,'draft')
    with self.assertRaises(ValueError):imp.normalize(source,'source','r1',None,None,'public')
    with self.assertRaises(ValueError):imp.normalize([{'id':'../escape','kind':'location','name':'X'}],'source','r1',None,None,'draft')
 def test_public_feed_and_hex_cell(self):
    rows=self.records()
    with server.connect() as db:
      imp.import_records(db,rows,'test-source','rev1','a'*64,'json',apply=True)
    http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    worker=threading.Thread(target=http.serve_forever,daemon=True);worker.start()
    base='http://127.0.0.1:'+str(http.server_port)
    def get(path):
       with urlopen(base+path,timeout=5) as response:return json.load(response)
    try:
       feed=get('/api/v1/changes?since=0')
       self.assertEqual(feed['changed_objects'],[])
       cell=get('/api/v1/hex-cells/ALT-HX-L0-Q0-R0-K0/contents')
       self.assertEqual(cell['objects'],[])
       with server.connect() as db:
         db.execute("UPDATE entities SET visibility='public' WHERE id IN (?,?)",('ALT-HX-L0-Q0-R0-K0','ALT-LOC-DEMO'))
       feed=get('/api/v1/changes?since=0')
       self.assertEqual(set(feed['changed_objects']),{'ALT-LOC-DEMO','ALT-HX-L0-Q0-R0-K0'})
       cell=get('/api/v1/hex-cells/ALT-HX-L0-Q0-R0-K0/contents')
       self.assertEqual(set(cell['objects']),{'ALT-LOC-DEMO','ALT-HX-L0-Q0-R0-K0'})
       old=feed['revision']
       with server.connect() as db:db.execute("UPDATE entities SET visibility='restricted' WHERE id='ALT-LOC-DEMO'")
       change=get('/api/v1/changes?since='+str(old))
       self.assertEqual(change['withdrawn_objects'],['ALT-LOC-DEMO'])
    finally:
       http.shutdown();http.server_close();worker.join(timeout=3)
if __name__=='__main__':unittest.main()
