const PROOFS_KEY='pap.research.receipts';
export function savedProofs(){try{const a=JSON.parse(localStorage.getItem(PROOFS_KEY)||'[]');return Array.isArray(a)?a.filter(x=>typeof x==='string').slice(-50):[];}catch{return [];}}
let memoryProofs=[];
export function rememberProof(proof){if(!proof)return;memoryProofs=[...new Set([...savedProofs(),...memoryProofs,proof])].slice(-50);try{localStorage.setItem(PROOFS_KEY,JSON.stringify(memoryProofs));}catch{/* keep current browser context proof */}}
export function availableProofs(){return [...new Set([...savedProofs(),...memoryProofs])].slice(-50);}
export async function researchInfo(){const r=await fetch('/api/research/info/',{cache:'no-store'});if(!r.ok)throw Error('Informações indisponíveis');return r.json();}
export async function researchPost(path,data){
  const info=await researchInfo();
  const r=await fetch('/api/research/'+path+'/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':info.csrf},body:JSON.stringify(data)});
  if(!r.ok)throw Error('Não foi possível enviar. Tente novamente.');return r.json();
}
