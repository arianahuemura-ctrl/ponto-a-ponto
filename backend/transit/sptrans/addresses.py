"""Photon address suggestions: search-as-you-type with a bounded result set."""
import hashlib
import json
import math
import re
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError
from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


def split_number(query):
    """Accept '123 Rua X', 'Rua X 123' and 'Rua X, 123, bairro'."""
    leading=re.match(r'^\s*(\d+[A-Za-z]?)\s*,?\s+(.+)$',query)
    if leading:return leading[2],leading[1]
    trailing=re.match(r'^(.*?)[,\s]+(?:n[º°o.]?\s*)?(\d+[A-Za-z]?)(?=\s*(?:,|$))(.*)$',query,re.I)
    if trailing:return (trailing[1]+trailing[3]).strip(),trailing[2]
    return query,''


def street_key(value):
    value=unicodedata.normalize('NFKD',value.casefold()).encode('ascii','ignore').decode()
    value=value.split(',')[0]
    value=re.sub(r'\s+\d+[a-z]?$', '',value)
    value=re.sub(r'[^a-z0-9 ]','',value)
    words=value.split()
    aliases={'r':'rua','av':'avenida','al':'alameda','tv':'travessa','pca':'praca','estr':'estrada','dr':'doutor','prof':'professor','eng':'engenheiro','engº':'engenheiro','engª':'engenheira','dep':'deputado','pres':'presidente','ver':'vereador','cel':'coronel','brig':'brigadeiro','cons':'conselheiro'}
    return ' '.join(aliases.get(w,w) for w in words)


def suggest(query):
    base=getattr(settings,'PHOTON_URL','https://photon.komoot.io/api/').rstrip('/')+'/'
    key='pap.address.v2:'+hashlib.sha256((base+query.casefold()).encode()).hexdigest()
    cached=cache.get(key)
    if cached is not None:return cached
    street_query,number=split_number(query)
    normalized=street_query+' '+number if number else query
    params=urlencode({'q':normalized,'lat':-23.5505,'lon':-46.6333,'bbox':'-46.95,-24.05,-46.25,-23.25','limit':12,'dedupe':0})
    request=Request(base+'?'+params,headers={'User-Agent':'Ponto-a-Ponto/1.0 (UNIVESP academic travel planner)','Accept':'application/json'})
    with urlopen(request,timeout=8) as response: payload=json.load(response)
    results=[];seen=set()
    for feature in payload.get('features',[]):
        p=feature.get('properties',{});coordinates=feature.get('geometry',{}).get('coordinates',[])
        if len(coordinates)!=2:continue
        lon,lat=map(float,coordinates)
        if not math.isfinite(lat) or not math.isfinite(lon) or not (-24.05<=lat<=-23.25 and -46.95<=lon<=-46.25):continue
        street=p.get('street') or p.get('name')
        if not street:continue
        if number and str(p.get('housenumber','')).casefold()!=number.casefold():continue
        name=', '.join(str(v) for v in (street,p.get('housenumber')) if v)
        district=p.get('district') or p.get('locality') or p.get('suburb') or ''
        city=p.get('city') or p.get('town') or p.get('municipality') or ''
        postcode=p.get('postcode','')
        identity=(name,district,city,postcode)
        if identity in seen:continue
        seen.add(identity)
        label=', '.join(str(v) for v in (name,district,city,postcode) if v)
        results.append({'id':str(p.get('osm_type',''))+str(p.get('osm_id',len(results))),
                        'street':street,'number':p.get('housenumber') if number else None,'kind':'address' if number or p.get('osm_key')!='highway' else 'street','name':name,'district':district,'city':city,'postcode':postcode,'label':label,'lat':lat,'lon':lon})
    cache.set(key,results,600)
    return results

@require_GET
def suggestions(request):
    query=request.GET.get('q','').strip()
    if len(query)<3:return JsonResponse({'suggestions':[]})
    if len(query)>300:return JsonResponse({'error':'Informe até 300 caracteres.'},status=400)
    try:return JsonResponse({'suggestions':suggest(query)})
    except (URLError,TimeoutError,OSError,ValueError,TypeError,KeyError,AttributeError):
        return JsonResponse({'error':'Não foi possível buscar endereços agora. Tente novamente.'},status=502)
