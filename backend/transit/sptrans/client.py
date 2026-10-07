"""Cliente HTTPS Olho Vivo com cookies, reautenticação, timeout e cache curto."""
import http.cookiejar
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from django.conf import settings
from django.core.cache import cache

class APIError(Exception):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class OlhoVivo:
    def __init__(self):
        self.lock=threading.RLock()
        self.authenticated=False
        self.opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.opener.addheaders=[('User-Agent','PontoAPonto/1.0 (UNIVESP academic project)'),('Accept','application/json')]

    def _request(self,path,params=None,post=False):
        url='https://api.olhovivo.sptrans.com.br/v2.1/'+path+'?'+urllib.parse.urlencode(params or {})
        request=urllib.request.Request(url,data=b'' if post else None)
        with self.opener.open(request,timeout=8) as response:
            return json.load(response)

    def get(self,path,params=None,ttl=30):
        key='sptrans:'+path+':'+urllib.parse.urlencode(params or {})
        cached=cache.get(key)
        if cached is not None: return cached
        with self.lock:
            blocked=cache.get('sptrans:unavailable')
            if blocked: raise APIError(blocked)
            try:
                if not settings.SPTRANS_TOKEN:
                    raise APIError('Token SPTrans não configurado no servidor.')
                for attempt in range(2):
                    if not self.authenticated:
                        if self._request('Login/Autenticar',{'token':settings.SPTRANS_TOKEN},True) is not True:
                            raise APIError('A SPTrans não aceitou o token. Confira a credencial no servidor.')
                        self.authenticated=True
                    try:
                        result=self._request(path,params)
                        cache.set(key,result,ttl)
                        return result
                    except urllib.error.HTTPError as error:
                        if error.code==401 and attempt==0:
                            self.authenticated=False
                            continue
                        raise
            except APIError as error:
                cache.set('sptrans:unavailable',str(error),20)
                raise
            except (OSError, ValueError) as error:
                # Never expose exception URLs: authentication URLs contain the token.
                message='SPTrans indisponível no momento. Tente novamente em instantes.'
                cache.set('sptrans:unavailable',message,20)
                raise APIError(message) from None

client=OlhoVivo()
