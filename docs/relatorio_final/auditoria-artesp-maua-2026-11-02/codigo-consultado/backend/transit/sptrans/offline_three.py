"""Composição exata offline de três ônibus, agrupando extremidades em torno do trecho intermediário."""
import heapq
import sqlite3
import time


def rank_three(db,origin,destination,limit,deadline,shared=None,allows=None):
    if allows is not None and shared is not None:
        raise ValueError("Não compartilhar prefixos filtrados entre destinos.")
    if origin==destination:return []
    def check():
        if time.perf_counter()>deadline:raise sqlite3.OperationalError('interrupted')
    # Históricos com restrições idênticas nas extremidades são estruturalmente intercambiáveis.
    # Mantenha K por classe de equivalência, nunca K globais nas paradas intermediárias.
    def retain(mapping,key,group,value):
        groups=mapping.setdefault(key,{})
        values=groups.setdefault(group,[])
        values.append(value);values.sort();del values[limit:]
    # O cache pertence a uma única origem e ao mesmo artefato durante a materialização.
    key=(origin,limit)
    cached=shared.get(key) if shared is not None else None
    prefix={}
    sql='''SELECT t.outgoing_pattern,t.boarding_index,a.id,a.destination,
        a.distance_meters+coalesce(w.distance_meters,0),t.walk_id,coalesce(w.distance_meters,0),coalesce(w.seconds,0)
        FROM ride_edge a CROSS JOIN transfer t INDEXED BY transfer_out
        JOIN occurrence o ON o.pattern_id=t.outgoing_pattern AND o.position=t.boarding_index
        LEFT JOIN walking_link w ON w.id=t.walk_id
        WHERE a.origin=? AND a.distance_meters IS NOT NULL
        AND t.incoming_pattern=a.pattern_id AND t.alighting_index=a.alighting_index
        AND (t.walk_id IS NULL OR (o.stop<>a.origin AND NOT EXISTS (SELECT 1 FROM occurrence k
            WHERE k.pattern_id=a.pattern_id AND k.stop=o.stop AND k.position>a.boarding_index)))'''
    for idx,r in enumerate(db.execute(sql,(origin,)) if cached is None else ()):
        if idx%10000==0:check()
        if allows is not None and not allows(r[2]):continue
        # (custo, ID da aresta, desembarque anterior, ID da caminhada, distância e segundos a pé)
        retain(prefix,(r[0],r[1]),r[3],(r[4],r[2],r[3],r[5] or 0,r[6],r[7]))
    if cached is not None:
        prefix=cached[0]
    if not prefix:return []
    reusable_prefix=prefix
    # A exclusão pelo destino continua sendo aplicada antes da seleção final.
    prefix={k:{g:values for g,values in groups.items() if g!=destination}
            for k,groups in prefix.items()}
    prefix={k:g for k,g in prefix.items() if g}
    patterns={k[0] for k in prefix}
    suffix={}
    sql='''SELECT u.incoming_pattern,u.alighting_index,c.edge_id,c.origin,c.destination,
        c.distance_meters+coalesce(w.distance_meters,0),u.walk_id,c.walk_id,
        c.walk_meters+coalesce(w.distance_meters,0),c.walk_seconds+coalesce(w.seconds,0)
        FROM one_bus c CROSS JOIN transfer u INDEXED BY transfer_in
        LEFT JOIN walking_link w ON w.id=u.walk_id
        WHERE c.destination=? AND c.distance_meters IS NOT NULL
        AND u.outgoing_pattern=c.pattern_id AND u.boarding_index=c.boarding_index'''
    # c.destination em one_bus é o destino FINAL; o desembarque físico do último ônibus
    # é obtido separadamente para preservar as exclusões antes da caminhada final.
    sql=sql.replace('c.origin,c.destination,','c.origin,e.destination,').replace(
        'LEFT JOIN walking_link w ON w.id=u.walk_id','JOIN ride_edge e ON e.id=c.edge_id LEFT JOIN walking_link w ON w.id=u.walk_id')
    for idx,r in enumerate(db.execute(sql,(destination,))):
        if idx%10000==0:check()
        if r[0] not in patterns or r[4]==origin:continue
        if allows is not None and not allows(r[2]):continue
        # (custo, última aresta, caminhada final, origem/destino do ônibus, caminhada de transferência, metros/segundos a pé)
        retain(suffix,(r[0],r[1]),(r[3],r[4]),(r[5],r[2],r[7] or 0,r[3],r[4],r[6] or 0,r[8],r[9]))
    if not suffix:return []
    prefix={k:sorted(v for group in g.values() for v in group) for k,g in prefix.items()}
    suffix={k:sorted(v for group in g.values() for v in group) for k,g in suffix.items()}
    if cached is None:
        occurrences={}
        for pid,stop,pos in db.execute('SELECT pattern_id,stop,max(position) FROM occurrence GROUP BY pattern_id,stop'):
            check()
            occurrences[pid,stop]=pos
        middle=[]
        for idx,b in enumerate(db.execute('SELECT id,origin,destination,pattern_id,boarding_index,alighting_index,distance_meters FROM ride_edge WHERE distance_meters IS NOT NULL')):
            if idx%10000==0:check()
            if allows is not None and not allows(b[0]):continue
            if b[2]!=origin and (b[3],b[4]) in reusable_prefix:
                middle.append(tuple(b))
        cached=(reusable_prefix,occurrences,middle)
        # Só publique preparação completa; timeout nunca reutiliza dados parciais.
        if shared is not None:
            shared.clear()
            shared[key]=cached
    _,occurrences,middle=cached
    heap=[]
    for idx,b in enumerate(middle):
        if idx%10000==0:check()
        if b[2]==destination:continue
        p=prefix.get((b[3],b[4]));s=suffix.get((b[3],b[5]))
        if p and s:heap.append((p[0][0]+b[6]+s[0][0],b))
    heapq.heapify(heap)
    best=[]
    rank=lambda r:(r['distance_meters'],r['edge1'],r['edge2'],r['edge3'],-1 if r['final_walk'] is None else r['final_walk'])
    while heap:
        check();lower,b=heapq.heappop(heap)
        if len(best)>=limit and lower>best[-1]['distance_meters']+1e-7:break
        pp=prefix[b[3],b[4]]
        ss=[s for s in suffix[b[3],b[5]] if b[2]!=s[4] and
            (not s[5] or (s[3]!=b[1] and occurrences.get((b[3],s[3]),-1)<=b[4]))]
        if not ss:continue
        queue=[(p[0]+b[6]+ss[0][0],i,0) for i,p in enumerate(pp)]
        heapq.heapify(queue)
        while queue:
            check();distance,i,j=heapq.heappop(queue)
            if len(best)>=limit and distance>best[-1]['distance_meters']+1e-7:break
            p,s=pp[i],ss[j]
            if p[2]!=s[4]:
                wm=p[4]+s[6];ws=p[5]+s[7]
                best.append(dict(origin=origin,destination=destination,boardings=3,edge1=p[1],edge2=b[0],edge3=s[1],
                    walk1=p[3] or None,walk2=s[5] or None,final_walk=s[2] or None,
                    bus_meters=distance-wm,walk_meters=wm,walk_seconds=ws,distance_meters=distance))
                best.sort(key=rank);del best[limit:]
            if j+1<len(ss):heapq.heappush(queue,(p[0]+b[6]+ss[j+1][0],i,j+1))
    for row in best:
        distances=[db.execute('SELECT distance_meters FROM ride_edge WHERE id=?',(row[f'edge{i}'],)).fetchone()[0] for i in (1,2,3)]
        row['bus_meters']=distances[0]+distances[1]+distances[2]
        walks=[db.execute('SELECT distance_meters,seconds FROM walking_link WHERE id=?',(row[key],)).fetchone() if row[key] else (0,0) for key in ('walk1','walk2','final_walk')]
        row['walk_meters']=walks[0][0]+walks[1][0]+walks[2][0];row['walk_seconds']=walks[0][1]+walks[1][1]+walks[2][1]
        row['distance_meters']=row['bus_meters']+row['walk_meters']
    best.sort(key=rank)
    return best
