"""BareBones Projects: HTTP auth, CSRF and public-data exposure regression tests."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('altdb_api',ROOT/'backend'/'server.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)

class APIIntegrationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.original_db=app.DATABASE
  app.DATABASE=Path(self.temp.name)/'test.sqlite3'
  app.init_db()
  app.bootstrap_admin('admin','a strong sample password 123!')
  self.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.base='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
  app.DATABASE=self.original_db;self.temp.cleanup()
 def request(self,path,payload=None,cookie=None,csrf=None):
  headers={}
  if cookie:headers['Cookie']=cookie
  if csrf:headers['X-CSRF-Token']=csrf
  if payload is not None:headers['Content-Type']='application/json'
  req=Request(self.base+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
  try:
   with urlopen(req,timeout=5) as r:return r.status,json.load(r),r.headers
  except HTTPError as error:return error.code,json.load(error),error.headers
 def test_auth_and_public_data_isolation(self):
  code,_,_=self.request('/admin');self.assertEqual(code,401)
  code,_,_=self.request('/api/v1/admin/entities');self.assertEqual(code,401)
  code,data,headers=self.request('/api/v1/admin/login',{'username':'admin','password':'incorrect password'})
  self.assertEqual(code,401)
  code,data,headers=self.request('/api/v1/admin/login',{'username':'admin','password':'a strong sample password 123!'})
  self.assertEqual(code,200)
  cookie=headers['Set-Cookie'].split(';',1)[0]
  code,session,_=self.request('/api/v1/admin/session',cookie=cookie)
  self.assertEqual(code,200)
  record={'id':'TEST-PLANET','kind':'planet','name':'Invisible Draft','visibility':'draft','data':{'x':12}}
  code,data,_=self.request('/api/v1/admin/entities',record,cookie=cookie)
  self.assertEqual(code,403)
  code,data,_=self.request('/api/v1/admin/entities',record,cookie=cookie,csrf=session['csrf_token'])
  self.assertEqual(code,200)
  code,public,_=self.request('/api/v1/planets')
  self.assertEqual(code,200)
  self.assertEqual(public['entries'],[])
  record['visibility']='public'
  code,data,_=self.request('/api/v1/admin/entities',record,cookie=cookie,csrf=session['csrf_token'])
  self.assertEqual(code,200)
  code,public,_=self.request('/api/v1/planets')
  self.assertEqual(len(public['entries']),1)
  self.assertEqual(public['entries'][0]['data']['x'],12)
  code,data,_=self.request('/api/v1/admin/logout',{},cookie=cookie,csrf=session['csrf_token'])
  self.assertEqual(code,200)
  code,_,_=self.request('/api/v1/admin/entities',cookie=cookie)
  self.assertEqual(code,401)
if __name__=='__main__':unittest.main()
