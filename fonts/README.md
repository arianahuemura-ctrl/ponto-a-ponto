# Fontes do cadastro de transporte

- `sources.json`: manifesto das fontes externas e sua finalidade.
- `collect.py`: coleta pública, com cache local e procedência; biblioteca padrão do Python.
- `osm.json`: recorte Overpass obtido em 23/09/2026; © colaboradores do OpenStreetMap, ODbL.
- `raw/`: respostas originais e metadados SHA-256/data/URL, gerados pelo coletor.
- `collected.json`: paradas, variantes, sequências e catálogo dos documentos coletados.

Execute `python backend/manage.py import_sources --download` na raiz do projeto.
Sem `--download`, o comando importa os arquivos locais; `--refresh` com `--download`
refaz a coleta. `--demo` importa explicitamente os horários, veículos e linhas fictícios.
Veja as limitações de cobertura e o uso do catálogo no README principal.

Não se presume equivalência entre IDs de fontes distintas, nem se inventam coordenadas
para endereços de paradas. Documentos históricos são referência, não rede vigente.

## Conversão de endereços

`download_geolocation.py` coleta o recorte descrito em `geolocation.overpass`.
`geolocation_osm.json` e `geolocation_osm.meta.json` preservam a entrada e sua procedência.
`geolocation_runs/` contém as decisões por execução. Execute
`python backend/manage.py geolocate_stops --download` na raiz do projeto.

Veja [o algoritmo e o inventário completo](../docs/IMPORTACOES_E_GEOLOCALIZACAO.md).
