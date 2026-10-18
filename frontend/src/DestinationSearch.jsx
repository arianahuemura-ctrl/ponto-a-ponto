import {useEffect,useRef,useState} from 'react';
import {api} from './api.js';
import {parseCoordinates} from './coordinates.js';
export default function DestinationSearch({open,onClose,onSelect,onStreet,onCoordinates,origin,role='destination'}) {
  const dialog=useRef(),input=useRef(),selectionRequest=useRef();
  const [query,setQuery]=useState(''),[suggestions,setSuggestions]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[result,setResult]=useState(null),[active,setActive]=useState(-1),[retry,setRetry]=useState(0),[choosing,setChoosing]=useState(false),[finished,setFinished]=useState(false);
  useEffect(()=>{
    if(open){dialog.current.showModal();input.current?.focus();}
    else{dialog.current.close();selectionRequest.current?.abort();setChoosing(false);}
  },[open]);
  useEffect(()=>()=>selectionRequest.current?.abort(),[]);
  useEffect(()=>{
    setSuggestions([]);setActive(-1);setFinished(false);setBusy(false);
    if(!open||query.trim().length<3||result)return;
    const coordinates=parseCoordinates(query);
    if(coordinates){
      setError(coordinates.error||'');
      if(!coordinates.error)setSuggestions([{...coordinates,id:'coordinates',kind:'coordinates',name:'Ver localização no mapa',district:'Raio de 250 m',label:query.trim()}]);
      return;
    }
    const abort=new AbortController();setBusy(true);setError('');
    const timer=setTimeout(()=>api('sptrans/addresses',{q:query.trim()},abort.signal).then(data=>{
      if(!abort.signal.aborted){setSuggestions(data.suggestions);setFinished(true);}
    }).catch(e=>{if(!abort.signal.aborted)setError(e.message);}).finally(()=>{if(!abort.signal.aborted)setBusy(false);}),500);
    return()=>{clearTimeout(timer);abort.abort();};
  },[open,query,retry,result]);
  const choose=async place=>{
    if(place.kind==='coordinates'){selectionRequest.current?.abort();onCoordinates({lat:place.lat,lon:place.lon});setQuery('');setSuggestions([]);onClose();return;}
    selectionRequest.current?.abort();const abort=new AbortController();selectionRequest.current=abort;setChoosing(true);setError('');
    try{
      const data=await api('sptrans/destination',{lat:place.lat,lon:place.lon,...(place.kind==='street'?{street:place.street}:role==='destination'&&origin?{origin:origin.id}:{})},abort.signal);
      if(!abort.signal.aborted){if(place.kind==='street'){if(data.stops?.length){onStreet({...data,label:place.label});onClose();}else setError(data.message);return;}if(data.stop)setResult({...data,place});else setError(data.message);}
    }catch(e){if(!abort.signal.aborted)setError(e.message);}
    finally{if(!abort.signal.aborted)setChoosing(false);}
  };
  const name=role==='origin'?'embarque':'destino';
  return <dialog ref={dialog} className="sp-stop-dialog sp-destination-search" aria-labelledby="destination-title" onCancel={onClose}>
    <button className="text-button" onClick={onClose} aria-label="Fechar busca de endereço">Fechar ×</button>
    <h2 id="destination-title">{role==='origin'?'Onde você vai embarcar?':'Para onde você vai?'}</h2>
    <form onSubmit={e=>{e.preventDefault();if(active>=0&&suggestions[active])choose(suggestions[active]);else if(suggestions[0]?.kind==='coordinates')choose(suggestions[0]);else setRetry(n=>n+1);}}>
      <label className="sp-search-label">Endereço ou coordenadas de {name}<input ref={input} value={query} maxLength={300} autoComplete="off" role="combobox" aria-autocomplete="list" aria-expanded={suggestions.length>0&&!result} aria-controls="address-options" aria-activedescendant={active>=0?`address-option-${active}`:undefined} placeholder="Rua, lugar ou latitude, longitude" onChange={e=>{selectionRequest.current?.abort();setChoosing(false);setResult(null);setQuery(e.target.value);setError('');}} onKeyDown={e=>{
        if(e.key==='ArrowDown'&&suggestions.length){e.preventDefault();setActive(a=>(a+1)%suggestions.length);}
        if(e.key==='ArrowUp'&&suggestions.length){e.preventDefault();setActive(a=>a<=0?suggestions.length-1:a-1);}
      }}/></label>
    </form>
    {busy&&<p role="status">Buscando sugestões…</p>}
    {choosing&&<p role="status">Localizando a parada mais próxima…</p>}
    {error&&<p role="alert">{error}<button className="text-button" onClick={()=>setRetry(n=>n+1)}>Tentar novamente</button></p>}
    {!result&&<ul id="address-options" role="listbox" aria-label="Endereços encontrados" className="sp-address-options">{suggestions.map((place,i)=><li key={place.id+':'+i} id={`address-option-${i}`} role="option" aria-selected={active===i} onMouseDown={e=>e.preventDefault()} onClick={()=>choose(place)}>
      <strong>{place.name}</strong><span>{place.district||'Bairro não informado'}{place.city?` · ${place.city}`:''}{place.postcode?` · ${place.postcode}`:''}</span>
    </li>)}</ul>}
    {finished&&!busy&&!suggestions.length&&!result&&!error&&<p>Nenhum endereço encontrado. Acrescente o bairro ou o número.</p>}
    {result&&<section><h3>Confirme o {name}</h3><p>{result.place.label}</p><p><strong>Parada sugerida:</strong> {result.stop.name} · {result.stop.id}</p><p>{result.distance_meters} m em linha reta; a caminhada pode ser maior.</p>
      {role==='origin'&&<p>O sentido do embarque será conferido quando você escolher o destino.</p>}
      {result.direction_checked&&<p>Sentido verificado a partir do embarque, priorizando menos trocas entre paradas próximas.</p>}
      <button className="primary full" onClick={()=>{onSelect({...result.stop,destinationAddress:result.place.label,addressDistance:result.distance_meters,addressCoordinates:{lat:result.place.lat,lon:result.place.lon},addressMaxTransfers:result.max_transfers});onClose();}}>Usar como {name}</button>
      <button className="text-button" onClick={()=>setResult(null)}>Escolher outro endereço</button></section>}
    <small>Coordenadas: −23.559010, −46.731544. A busca centraliza o mapa com raio de 250 m, sem alterar embarque ou destino.</small>
    <small>Sugestões: Photon / OpenStreetMap. Sem número, escolha a rua para ver suas paradas. Com número, selecione o endereço completo.</small>
  </dialog>;
}
