// BareBones Projects, Designed by: Justin Levesque-Welsch.
import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeEntries,selectEntries,makeApiUrl} from '../scripts/data.mjs';
test('extract API entries',()=>assert.equal(normalizeEntries({entries:[{id:'x',visibility:'public'}]}).length,1));
test('exclude draft/private items defensively',()=>assert.deepEqual(normalizeEntries({entries:[{visibility:'draft'},{visibility:'private'},{kind:'planet'}]}),[{kind:'planet'}]));
test('fandom filters categories',()=>assert.equal(selectEntries([{kind:'planet'},{kind:'character'}],'fandom').length,1));
test('wiki searches all categories',()=>assert.equal(selectEntries([{kind:'planet',name:'Primus'}],'wiki','primus').length,1));
test('alt filters nav data',()=>assert.equal(selectEntries([{kind:'planet'},{kind:'character'}],'alt').length,1));
test('safe URL construction',()=>assert.equal(makeApiUrl('https://api.example/','api/v1/entities'),'https://api.example/api/v1/entities'));
test('reject credentials',()=>assert.throws(()=>makeApiUrl('https://user:password@api.example/','api/v1/entities')));