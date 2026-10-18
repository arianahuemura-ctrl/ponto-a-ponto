import PointIcon from './PointIcon.jsx';
import {useEffect,useRef} from 'react';
import Icon from './Icon.jsx';
export default function FavoritesDialog({open,favorites,onClose,onSelect,onPreview,onEdit,onRemove,onLocation,hasLocation}) {
  const dialog=useRef();
  useEffect(()=>{const el=dialog.current;if(open&&!el.open)el.showModal();else if(!open&&el.open)el.close();},[open]);
  return <dialog ref={dialog} className="sp-stop-dialog sp-board-dialog sp-favorites-dialog" aria-labelledby="favorites-title" onCancel={onClose}>
    <header className="sp-board-top"><h2 id="favorites-title">Pontos favoritos</h2><div className="sp-board-window-actions"><button className="icon-button" aria-label="Ver mapa" title="Ver mapa" onClick={onClose}><Icon name="map"/></button><button className="icon-button" aria-label="Fechar favoritos" title="Fechar favoritos" onClick={onClose}><Icon name="close"/></button></div></header>
    <p>Use um favorito como destino, embarque ou consulte os próximos ônibus.</p>
    {hasLocation&&<div className="sp-board-actions"><button className="text-button" onClick={()=>onLocation('origin')}><Icon name="locate"/> Minha localização como origem</button><button className="text-button" onClick={()=>onLocation('destination')}><Icon name="locate"/> Minha localização como destino</button></div>}
    {!favorites.length&&<p>Adicione pontos aos favoritos usando a estrela.</p>}
    <div className="sp-favorite-cards">{favorites.map(s=>{const name=s.favoriteLabel||s.name;return <article className="sp-favorite-card" key={s.id}>
      <div className="sp-favorite-name"><Icon name="star"/><div><strong>{name}</strong><small>{s.name} · {s.id}</small></div></div>
      <div className="sp-favorite-tools">{[['finish','Usar como destino',()=>onSelect(s,'destination')],['bus','Usar como embarque',()=>onSelect(s,'origin')],['eye','Ver próximos ônibus',()=>onPreview(s)],['edit','Renomear favorito',()=>onEdit(s)],['trash','Remover favorito',()=>onRemove(s)]].map(([icon,label,action])=><button key={icon} className="icon-button sp-favorite-point-icon" data-kind={icon==='bus'?'origin':icon==='finish'?'destination':undefined} aria-label={label+' '+name} title={label} onClick={action}>{icon==='bus'||icon==='finish'?<PointIcon kind={icon==='bus'?'origin':'destination'}/>:<Icon name={icon} viewBox={icon==='eye'?'1.1 4.1 21.8 15.8':'2.1 2.1 19.8 19.8'} style={{width:icon==='eye'?38.6:28,height:28}}/>}</button>)}</div>
    </article>;})}</div>
  </dialog>;
}
