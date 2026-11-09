// BareBones Projects, Designed by: Justin Levesque-Welsch.
import {normalizeEntries, selectEntries, makeApiUrl} from './data.mjs';
const view=document.body.dataset.view;
const message=document.querySelector('#message'), grid=document.querySelector('#records'), search=document.querySelector('#search');
const base=(window.ALT_WEB_CONFIG?.apiBaseUrl ?? '').trim();
let items=[];
function render(){
  const matches=selectEntries(items,view,search.value);
  grid.replaceChildren();
  for(const entry of matches.slice(0,500)){
    const article=document.createElement('article');article.className='record';
    const kind=document.createElement('small');kind.textContent=String(entry.kind ?? entry.type ?? 'ENTRY');
    const title=document.createElement('h2');title.textContent=String(entry.name ?? entry.title ?? entry.id ?? 'Untitled');
    const desc=document.createElement('p');desc.textContent=String(entry.description ?? entry.summary ?? entry.data?.description ?? 'Public record');
    article.append(kind,title,desc);grid.append(article);
  }
  message.textContent=matches.length ? `Showing ${Math.min(matches.length,500)} of ${matches.length} matching public entries.` : 'No matching public entries.';
}
search.addEventListener('input',render);
async function load(){
 if(!base){message.textContent='API not configured. Set the public read-only API URL in config.js to load records.';return;}
 try{
  const url=makeApiUrl(base,'api/v1/entities');
  const response=await fetch(url,{method:'GET',mode:'cors',credentials:'omit',headers:{Accept:'application/json'},signal:AbortSignal.timeout(12000)});
  if(!response.ok) throw new Error('API returned HTTP '+response.status);
  items=normalizeEntries(await response.json());
  render();
 }catch(error){message.textContent='Unable to load public records: '+error.message+'. Verify HTTPS, API availability and CORS.';}
}
load();