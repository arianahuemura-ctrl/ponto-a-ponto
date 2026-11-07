import Icon from './Icon.jsx';
export const quickDestinationLabels={home:'Casa',work:'Trabalho'};
export default function QuickDestinations({favorites,assignments,onSelect,onConfigure,editable=false}) {
  return <div className="sp-quick-destinations" role="group" aria-label="Destinos rápidos">{Object.entries(quickDestinationLabels).map(([role,label])=>{
    const stop=favorites.find(s=>s.id===assignments[role]);
    return <div className="sp-quick-destination" key={role}>
      <button type="button" className="sp-quick-go" aria-label={stop?`Ir para ${label}`:`Configurar ${label}`} title={stop?`${label}: ${stop.favoriteLabel||stop.name}`:`Escolher local para ${label}`} onClick={()=>stop?onSelect(stop,'destination'):onConfigure(role)}><Icon name={role}/><span>{label}</span>{!stop&&<small>Adicionar</small>}</button>
      {editable&&stop&&<button type="button" className="icon-button" aria-label={`Alterar atalho ${label}`} title={`Alterar ${label}`} onClick={()=>onConfigure(role)}><Icon name="edit"/></button>}
    </div>;
  })}</div>;
}
