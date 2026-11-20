// BareBones Projects, Designed by: Justin Levesque-Welsch.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
test('website homepage has no database-portal navigation',()=>{
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 for(const path of ['href="fandom-db/','href="wiki-db/','href="alt-db/']) assert.equal(html.includes(path),false);
});
test('database-owned portal directories are absent',()=>{
 for(const path of ['fandom-db','wiki-db','alt-db']) assert.equal(existsSync(new URL('../'+path,import.meta.url)),false);
});
test('deployment allowlist does not copy database portals',()=>{
 const workflow=readFileSync(new URL('../.github/workflows/pages.yml',import.meta.url),'utf8');
 assert.equal(workflow.includes('cp -R fandom-db'),false);
});