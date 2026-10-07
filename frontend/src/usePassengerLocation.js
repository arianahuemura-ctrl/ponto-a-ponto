import {useEffect, useState} from 'react';
import {api} from './api.js';
import {trackLocation} from './location.js';
export function usePassengerLocation() {
  const [position, setPosition] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    let stop = () => {};
    api('location-config', {}, controller.signal).then(config => {
      if (controller.signal.aborted) return;
      stop = trackLocation(config.position, navigator, window.isSecureContext,
        value => { if (!controller.signal.aborted) {setPosition(value); if(value)setError('');} },
        message => {if (!controller.signal.aborted) setError(message);});
    }).catch(e => {if (!controller.signal.aborted) setError(e.message);});
    return () => {controller.abort(); stop();};
  }, []);
  return {position, error};
}
