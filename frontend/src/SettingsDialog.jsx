import {useEffect,useRef} from 'react';
import Icon from './Icon.jsx';

export default function SettingsDialog({open,onClose,theme,onTheme}) {
  const dialog=useRef();
  useEffect(()=>{if(open)dialog.current.showModal();else dialog.current.close();},[open]);
  return <dialog ref={dialog} className="sp-stop-dialog sp-settings" data-private aria-labelledby="settings-title" onCancel={e=>{e.preventDefault();onClose();}}>
    <header><h2 id="settings-title">Configurações</h2><button type="button" className="icon-button" aria-label="Fechar configurações" onClick={onClose}><Icon name="close"/></button></header>
    <label className="sp-search-label">Aparência<select value={theme} onChange={e=>onTheme(e.target.value)}>
      <option value="system">Usar tema do aparelho</option><option value="light">Modo claro</option><option value="dark">Modo escuro</option>
    </select></label>
    <button type="button" className="secondary full" onClick={()=>{dialog.current.close();onClose();window.dispatchEvent(new Event('pap-open-research'));}}>Participação na pesquisa</button>
  </dialog>;
}
