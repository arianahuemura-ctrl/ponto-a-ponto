export async function api(path, params, signal) {
  const response = await fetch(
    "/api/" + path + "/?" + new URLSearchParams(params),
    { signal },
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error || "Falha ao consultar o servidor.");
  return data;
}
export function getLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation)
      return reject(new Error("Seu navegador não oferece geolocalização."));
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ lat: coords.latitude, lon: coords.longitude }),
      (error) =>
        reject(
          new Error(
            error.code === 1
              ? "Permissão de localização negada. Informe um endereço."
              : "Não foi possível obter sua localização.",
          ),
        ),
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 30000 },
    );
  });
}

export async function apiProgressive(path, params, signal, onResult) {
  const response = await fetch('/api/' + path + '/?' + new URLSearchParams(params), {signal});
  if (!response.ok) throw new Error('Falha ao consultar o servidor.');
  if (!response.headers.get('content-type')?.includes('application/x-ndjson')) {
    const result=await response.json();
    if(result.error)throw new Error(result.error);
    onResult(result);return;
  }
  const reader=response.body.getReader(),decoder=new TextDecoder();
  let buffer='';
  const receive=line=>{if(!line.trim()||signal.aborted)return;const result=JSON.parse(line);if(result.error)throw new Error(result.error);onResult(result);};
  try {
    while(true){
      const {value,done}=await reader.read();
      buffer+=decoder.decode(value,{stream:!done});
      const lines=buffer.split('\n');buffer=lines.pop();
      for(const line of lines)receive(line);
      if(done){receive(buffer);break;}
    }
  } finally {await reader.cancel().catch(()=>{});reader.releaseLock();}
}
