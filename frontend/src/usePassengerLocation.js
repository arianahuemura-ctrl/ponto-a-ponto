import {useEffect, useState} from 'react';
import {api} from './api.js';
import {trackLocation, locationParams} from './location.js';
export function usePassengerLocation() {
  const [params] = useState(() => locationParams(window.location.search));
  const [position, setPosition] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    let stop = () => {};
    api('location-config', params, controller.signal).then(config => {
      if (controller.signal.aborted) return;
      stop = trackLocation(config.position, navigator, window.isSecureContext,
        value => { if (!controller.signal.aborted) {setPosition(value); if(value)setError('');} },
        message => {if (!controller.signal.aborted) setError(message);});
    }).catch(e => {if (!controller.signal.aborted) setError(e.message);});
    return () => {controller.abort(); stop();};
  }, [params]);
  return {position, error};
}
