// BareBones Projects | ALT Database admin
let csrf;
const notice=document.querySelector('#notice');
async function api(path,options={}){
 const response=await fetch(path,{credentials:'same-origin',cache:'no-store',...options});
 if(!response.ok){const data=await response.json().catch(()=>({}));throw Error(data.error||'HTTP '+response.status)}
 return response.json();
}
async function post(path,body){
 return api(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)});
}
function rows(target,entries,fields){
 const node=document.querySelector(target);node.replaceChildren();
 for(const entry of entries){const tr=document.createElement('tr');for(const field of fields){const td=document.createElement('td');td.textContent=String(entry[field]??'');tr.append(td)}node.append(tr)}
}
async function refresh(){
 const [entities,media]=await Promise.all([api('/api/v1/admin/entities'),api('/api/v1/admin/media')]);
 rows('#entities',entities.entries,['id','kind','name','visibility']);
 rows('#media',media.entries,['id','filename','visibility']);
}
async function main(){
 const session=await api('/api/v1/admin/session');csrf=session.csrf_token;notice.textContent='Signed in as '+session.username;
 await refresh();
}
document.querySelector('#record').addEventListener('submit',async e=>{
 e.preventDefault();const f=new FormData(e.target);
 try{await post('/api/v1/admin/entities',{id:f.get('id'),kind:f.get('kind'),name:f.get('name'),parent_id:f.get('parent_id')||null,visibility:f.get('visibility'),data:JSON.parse(f.get('data'))});notice.textContent='Record saved';await refresh()}
 catch(err){notice.textContent=err.message}
});
document.querySelector('#upload').addEventListener('submit',async e=>{
 e.preventDefault();const f=new FormData(e.target),file=f.get('file');
 if(file.size>8*1024*1024){notice.textContent='File exceeds 8 MiB';return}
 try{
 const raw=new Uint8Array(await file.arrayBuffer());let binary='';
 for(let i=0;i<raw.length;i+=8192)binary+=String.fromCharCode(...raw.subarray(i,i+8192));
 await post('/api/v1/admin/media',{id:f.get('id'),entity_id:f.get('entity_id')||null,filename:file.name,mime:file.type||'application/octet-stream',visibility:f.get('visibility'),content_base64:btoa(binary)});
 notice.textContent='Media saved';await refresh();
 }catch(err){notice.textContent=err.message}
});
document.querySelector('#logout').addEventListener('click',async()=>{try{await post('/api/v1/admin/logout',{})}finally{location.href='/login'}});
main().catch(err=>{notice.textContent=err.message;location.href='/login'});
