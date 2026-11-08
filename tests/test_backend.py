import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('altdb',ROOT/'backend'/'server.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class BackendTests(unittest.TestCase):
 def test_schema_and_admin(self):
  with tempfile.TemporaryDirectory() as d:
   original=module.DATABASE
   try:
    module.DATABASE=Path(d)/'test.sqlite3'
    module.init_db()
    module.bootstrap_admin('tester','correct horse battery staple')
    with module.connect() as db:
     admin=db.execute('SELECT * FROM admins WHERE username=?',('tester',)).fetchone()
     self.assertEqual(admin['password_hash'],module.digest_password('correct horse battery staple',admin['salt']))
     db.execute("INSERT INTO entities(id,kind,name,visibility) VALUES (?,?,?,?)",('S01','planet','PRIME','public'))
     entity=db.execute("SELECT * FROM entities WHERE id='S01'").fetchone()
     self.assertEqual(module.public_entity(entity)['name'],'PRIME')
   finally:module.DATABASE=original
 def test_security_validation(self):
  self.assertNotIn('sql',module.ALLOWED_MIME)
  self.assertNotIn('application/x-sh',module.ALLOWED_MIME)
  self.assertFalse(module.ID_PATTERN.fullmatch('../escape'))
  self.assertEqual(len(module.KINDS),11)
if __name__=='__main__':unittest.main()
