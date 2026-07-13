from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CTV-AI Knowledge Admin</title>
<style>
:root{--bg:#0b0d10;--panel:#15191f;--panel2:#1c222a;--text:#f4f6f8;--muted:#9da7b3;--accent:#ff7a1a;--good:#45c486;--bad:#ff6670;--line:#2b333d}
*{box-sizing:border-box}body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text)}
header{padding:22px 28px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}
.brand{font-size:20px;font-weight:750}.brand span{color:var(--accent)}
main{max-width:1280px;margin:0 auto;padding:24px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}.span4{grid-column:span 4}.span6{grid-column:span 6}.span8{grid-column:span 8}.span12{grid-column:span 12}
h2{font-size:17px;margin:0 0 14px}label{display:block;color:var(--muted);font-size:12px;margin:10px 0 6px}
input,select,textarea,button{width:100%;border-radius:9px;border:1px solid var(--line);background:var(--panel2);color:var(--text);padding:11px}
textarea{min-height:110px;resize:vertical}button{cursor:pointer;background:var(--accent);border:none;font-weight:700;margin-top:10px}
button.secondary{background:#28313b}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.stat{background:var(--panel2);padding:13px;border-radius:10px}.stat b{display:block;font-size:22px}.stat span{color:var(--muted);font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted)}
.status-ready{color:var(--good)}.status-failed{color:var(--bad)}.small{font-size:12px;color:var(--muted)}
.source{background:var(--panel2);border-radius:10px;padding:12px;margin-top:10px}.hidden{display:none}
#toast{position:fixed;right:20px;bottom:20px;background:#222b35;border:1px solid var(--line);padding:12px 16px;border-radius:10px;display:none}
@media(max-width:900px){.span4,.span6,.span8,.span12{grid-column:span 12}.stats{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<header><div class="brand"><span>CTV-AI</span> Knowledge Admin</div><div id="identity" class="small">Not signed in</div></header>
<main>
<section id="loginPanel" class="card" style="max-width:460px;margin:40px auto">
<h2>Administrator Login</h2>
<label>Email</label><input id="email" type="email">
<label>Password</label><input id="password" type="password">
<button onclick="login()">Sign in</button>
<div id="loginError" class="small" style="color:var(--bad);margin-top:10px"></div>
</section>

<section id="appPanel" class="hidden">
<div class="grid">
<div class="card span12"><div class="stats">
<div class="stat"><b id="sTotal">0</b><span>Documents</span></div>
<div class="stat"><b id="sReady">0</b><span>Ready</span></div>
<div class="stat"><b id="sChunks">0</b><span>Chunks</span></div>
<div class="stat"><b id="sFailed">0</b><span>Failed</span></div>
</div></div>

<div class="card span4">
<h2>Upload Knowledge</h2>
<label>Category</label><input id="category" value="general">
<label>Document</label><input id="file" type="file" accept=".pdf,.docx,.txt,.md">
<button id="uploadBtn" onclick="uploadDocument()">Upload and Index</button>
<div id="uploadState" class="small" style="margin-top:10px"></div>
</div>

<div class="card span8">
<h2>Indexed Documents</h2>
<div style="overflow:auto"><table><thead><tr><th>File</th><th>Category</th><th>Status</th><th>Chunks</th><th></th></tr></thead><tbody id="documents"></tbody></table></div>
</div>

<div class="card span6">
<h2>Semantic Search Test</h2>
<label>Query</label><textarea id="searchQuery"></textarea>
<label>Category (optional)</label><input id="searchCategory">
<button onclick="runSearch()">Search</button>
<div id="searchResults"></div>
</div>

<div class="card span6">
<h2>Grounded Answer Test</h2>
<label>Question</label><textarea id="askQuestion"></textarea>
<label>Category (optional)</label><input id="askCategory">
<label>Assistant</label><select id="assistant"><option>general</option><option>production</option><option>graphics</option><option>drone</option><option>it</option><option>coder</option></select>
<button onclick="runAsk()">Ask Company Brain</button>
<div id="answerResult"></div>
</div>
</div>
</section>
</main>
<div id="toast"></div>
<script>
const API='/api/v1'; let token=localStorage.getItem('ctv_token')||'';
function toast(msg){const t=document.getElementById('toast');t.textContent=msg;t.style.display='block';setTimeout(()=>t.style.display='none',3000)}
function headers(json=true){const h={Authorization:'Bearer '+token};if(json)h['Content-Type']='application/json';return h}
async function login(){
 const body=new URLSearchParams();body.set('username',email.value);body.set('password',password.value);
 const r=await fetch(API+'/auth/login',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});
 if(!r.ok){loginError.textContent='Login failed';return}
 const d=await r.json();token=d.access_token;localStorage.setItem('ctv_token',token);await boot();
}
async function boot(){
 if(!token)return;
 const r=await fetch(API+'/auth/me',{headers:headers(false)});
 if(!r.ok){localStorage.removeItem('ctv_token');token='';return}
 const me=await r.json();identity.textContent=me.full_name+' · '+me.role;loginPanel.classList.add('hidden');appPanel.classList.remove('hidden');await Promise.all([loadStats(),loadDocuments()]);
}
async function loadStats(){
 const r=await fetch(API+'/knowledge/stats',{headers:headers(false)});if(!r.ok)return;
 const d=await r.json();sTotal.textContent=d.total_documents;sReady.textContent=d.ready_documents;sChunks.textContent=d.total_chunks;sFailed.textContent=d.failed_documents;
}
async function loadDocuments(){
 const r=await fetch(API+'/knowledge/documents',{headers:headers(false)});if(!r.ok)return;
 const docs=await r.json();documents.innerHTML=docs.map(d=>`<tr><td>${escapeHtml(d.filename)}<div class="small">${new Date(d.created_at).toLocaleString()}</div></td><td>${escapeHtml(d.category)}</td><td class="status-${d.status}">${d.status}</td><td>${d.chunk_count}</td><td><button class="secondary" onclick="removeDoc('${d.id}','${escapeAttr(d.filename)}')">Delete</button></td></tr>`).join('');
}
async function uploadDocument(){
 const f=file.files[0];if(!f){toast('Choose a file first');return}
 uploadBtn.disabled=true;uploadState.textContent='Uploading, extracting, embedding, and indexing...';
 const fd=new FormData();fd.append('file',f);fd.append('category',category.value||'general');
 const r=await fetch(API+'/knowledge/documents',{method:'POST',headers:headers(false),body:fd});
 const d=await r.json().catch(()=>({}));
 uploadBtn.disabled=false;
 if(!r.ok){uploadState.textContent=d.detail||'Upload failed';return}
 uploadState.textContent=`Ready: ${d.chunk_count} chunks`;file.value='';await Promise.all([loadStats(),loadDocuments()]);
}
async function removeDoc(id,name){
 if(!confirm('Delete '+name+' from PostgreSQL, Qdrant, and local storage?'))return;
 const r=await fetch(API+'/knowledge/documents/'+id,{method:'DELETE',headers:headers(false)});
 if(!r.ok){toast('Delete failed');return}toast('Document deleted');await Promise.all([loadStats(),loadDocuments()]);
}
async function runSearch(){
 searchResults.innerHTML='Searching...';
 const payload={query:searchQuery.value,top_k:5,category:searchCategory.value||null};
 const r=await fetch(API+'/knowledge/search',{method:'POST',headers:headers(),body:JSON.stringify(payload)});
 const d=await r.json();if(!r.ok){searchResults.textContent=d.detail||'Search failed';return}
 searchResults.innerHTML=d.sources.map(s=>`<div class="source"><b>${escapeHtml(s.filename)}</b> · score ${s.score.toFixed(3)}<div class="small">${escapeHtml(s.category)} ${s.page_number?'· page '+s.page_number:''}</div><p>${escapeHtml(s.text)}</p></div>`).join('')||'<p>No sources found.</p>';
}
async function runAsk(){
 answerResult.innerHTML='Generating grounded answer...';
 const payload={question:askQuestion.value,top_k:5,category:askCategory.value||null,assistant:assistant.value};
 const r=await fetch(API+'/knowledge/ask',{method:'POST',headers:headers(),body:JSON.stringify(payload)});
 const d=await r.json();if(!r.ok){answerResult.textContent=d.detail||'Request failed';return}
 answerResult.innerHTML=`<div class="source"><b>Answer</b><p>${escapeHtml(d.answer).replace(/\\n/g,'<br>')}</p></div>`+d.sources.map(s=>`<div class="source"><b>${escapeHtml(s.filename)}</b> · score ${s.score.toFixed(3)}<p>${escapeHtml(s.text)}</p></div>`).join('');
}
function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
function escapeAttr(v){return String(v??'').replace(/'/g,"\\'")}
boot();
</script>
</body>
</html>
"""


@router.get("/admin/knowledge", response_class=HTMLResponse)
async def knowledge_dashboard() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML)
