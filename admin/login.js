// BareBones Projects | ALT Database login
document.getElementById('login').addEventListener('submit',async event=>{
 event.preventDefault();
 const data=new FormData(event.currentTarget);
 try {
  const response=await fetch('/api/v1/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({username:data.get('username'),password:data.get('password')})});
  if(!response.ok)throw new Error('Invalid credentials');
  window.location.assign('/admin');
 }catch(error){document.getElementById('error').textContent=error.message}
});
