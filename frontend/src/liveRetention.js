// Cada fluxo mantém sua própria contagem; os horários de observação não são renovados.
export function retainLive() {
  let previous=null, failures=0;
  return (value,available)=>{
    if(available){previous=value;failures=0;return value;}
    failures++;
    if(failures<3&&previous!==null)return previous;
    previous=null;return value;
  };
}
