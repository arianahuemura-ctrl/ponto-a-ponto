"""Coleta pública reexecutável; conserva respostas e falhas sem exigir credenciais."""

import hashlib
import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent
BASE = "https://linhas.cittamobi.com.br"


def decode(body):
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("cp1252", errors="replace")


def clean(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


class Collector:
    def __init__(self, refresh=False):
        self.refresh = refresh
        self.documents = {}
        (ROOT / "raw").mkdir(exist_ok=True)

    def fetch(self, url, provider, kind="catalogue", payload=None):
        key = hashlib.sha256(
            (
                url
                + (json.dumps(payload, sort_keys=True) if payload is not None else "")
            ).encode()
        ).hexdigest()
        target = ROOT / "raw" / key
        meta = target.with_suffix(".json")
        document = dict(
            id=key, provider=provider, url=url, kind=kind, request_payload=payload
        )
        try:
            if target.exists() and meta.exists() and not self.refresh:
                document = json.loads(meta.read_text())
                body = target.read_bytes()
            else:
                time.sleep(0.2)
                with urlopen(
                    Request(
                        url,
                        data=(
                            json.dumps(payload).encode()
                            if payload is not None
                            else None
                        ),
                        headers={
                            "User-Agent": "MauaBusMap-academic-import/1.0",
                            "Content-Type": "application/json",
                        },
                    ),
                    timeout=40,
                ) as response:
                    body = response.read()
                    document.update(
                        content_type=response.headers.get("Content-Type", ""),
                        last_modified=response.headers.get("Last-Modified", ""),
                    )
                document.update(
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    sha256=hashlib.sha256(body).hexdigest(),
                    status="ok",
                    path=str(target.relative_to(ROOT)),
                )
                target.write_bytes(body)
                meta.write_text(json.dumps(document, ensure_ascii=False, indent=2))
            self.documents[key] = document
            return decode(body) if "pdf" not in document.get("content_type", "") else ""
        except Exception as exc:
            document.update(
                status="error",
                error=str(exc),
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            )
            self.documents[key] = document
            print(f"Falha: {provider}: {exc}", flush=True)
            return ""

    def run(self):
        sources = json.loads((ROOT / "sources.json").read_text())
        pages = {
            s["id"]: self.fetch(s["url"], s["id"], s["kind"], s.get("payload"))
            for s in sources
        }
        catalogue = pages["cittamobi"]
        base_url = next(s["url"] for s in sources if s["id"] == "cittamobi")
        visited = {base_url}
        while True:
            pending = {
                urljoin(base_url, html.unescape(link))
                for link in re.findall(r'href="([^" ]*\?page=\d+)"', catalogue)
            }
            pending = {
                url for url in pending if url.startswith(base_url + "?page=")
            } - visited
            if not pending:
                break
            for url in sorted(pending):
                visited.add(url)
                catalogue += self.fetch(url, "cittamobi")
        links = sorted(set(re.findall(r'href="(/linha/[^"?#]+)"', catalogue)))
        stops, routes = {}, []
        for index, link in enumerate(links):
            url = urljoin(BASE, html.unescape(link))
            page = self.fetch(url, "cittamobi")
            title = re.search(r"<title>Linha (.*?)</title>", page, re.S)
            cards = re.findall(
                r'data-stop-id="([^"]+)".*?<p class="p-18 stop-name">(.*?)</p>',
                page,
                re.S,
            )
            if not title or not cards:
                self.documents[hashlib.sha256(url.encode()).hexdigest()][
                    "parse_error"
                ] = "Estrutura de paradas/linha não reconhecida"
                print(f"Sem estrutura reconhecida: {url}", flush=True)
                continue
            label = clean(title.group(1)).split(": horários")[0]
            code, _, name = label.partition(" ")
            ordered = []
            for external_id, address in cards:
                sid = "cittamobi:" + external_id
                stops[sid] = dict(
                    id=sid,
                    name=clean(address),
                    address=clean(address),
                    lat=None,
                    lon=None,
                    source="cittamobi",
                    source_url=url,
                )
                ordered.append(sid)
            timetable = re.search(
                r'<script type="application/json" id="line-departures-v1">(.*?)</script>',
                page,
                re.S,
            )
            routes.append(
                dict(
                    id="cittamobi:" + link.rsplit("-", 1)[-1],
                    code=code,
                    name=name,
                    stops=ordered,
                    source="cittamobi",
                    source_url=url,
                    schedule=json.loads(timetable.group(1)) if timetable else {},
                )
            )
            # O PDF é a versão documental do mesmo itinerário.
            pdfs = set(re.findall(r'(?:href|data-pdf-url)="([^" ]+\.pdf)"', page))
            for pdf in pdfs:
                self.fetch(
                    urljoin(BASE, html.unescape(pdf)), "cittamobi", "itinerary_pdf"
                )
            print(
                f"{index+1}/{len(links)}: {code} {name} — {len(ordered)} paradas",
                flush=True,
            )
        for url, label in re.findall(
            r'<option value="(https://suzanturmaua.com.br/linhas/[^"]+)">(.*?)</option>',
            pages["suzantur"],
            re.S,
        ):
            title = clean(label)
            match = re.match(r"Linha\s+(\d+)\s*[–—-]?\s*(.*)", title)
            if not match:
                continue
            page = self.fetch(url, "suzantur", "official_itinerary")
            code, name = match.groups()
            routes.append(
                dict(
                    id="suzantur:" + url.rstrip("/").rsplit("/", 1)[-1],
                    code=code,
                    name=name,
                    source="suzantur",
                    source_url=url,
                    stops=[],
                    incomplete=True,
                )
            )
            for link in set(re.findall(r'href=["\']([^"\']+\.pdf)["\']', page)):
                self.fetch(
                    urljoin(url, html.unescape(link)), "suzantur", "official_pdf"
                )
        # Documento completo de exemplo: também preservado quando o HTML não expõe o link.
        self.fetch(
            BASE
            + "/maps/transporte_publico-Maua-Suzantur-Maua-088-ZAIRA-169f6fbfd86b.pdf",
            "cittamobi",
            "itinerary_pdf",
        )
        for row in re.findall(
            r"<tr\b[^>]*>(.*?)</tr>", pages["emtu_maua"], re.S | re.I
        ):
            cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S | re.I)
            link = re.search(r"'(/sistemas/linha/resultado1[^']+)'", row)
            if len(cells) < 3 or not link:
                continue
            url = urljoin("https://www.emtu.sp.gov.br", html.unescape(link.group(1)))
            self.fetch(url, "emtu", "official_itinerary")
            code, name = clean(cells[0]), clean(cells[1])
            routes.append(
                dict(
                    id="emtu:" + code,
                    code=code,
                    name=name,
                    source="emtu",
                    source_url=url,
                    stops=[],
                    incomplete=True,
                    scope="Consulta parcial por logradouro; não representa toda a cidade",
                )
            )
        article = (
            clean(pages["prefeitura2026"])
            .split("Confira abaixo os novos itinerários:")[-1]
            .split("Saúde Saúde")[0]
        )
        for code, name, text in re.findall(
            r"(71|75|76)\s*[–—-]\s*(.*?)\s+(Sentido Centro/Bairro:.*?)(?= (?:71|75|76)\s*[–—-]|Saúde de Mauá|$)",
            article,
        ):
            routes.append(
                dict(
                    id="prefeitura2026:" + code,
                    code=code,
                    name=name,
                    source="prefeitura2026",
                    source_url=next(
                        x["url"] for x in sources if x["id"] == "prefeitura2026"
                    ),
                    stops=[],
                    street_itinerary=text,
                    effective_date="2026-02-28",
                    incomplete=True,
                )
            )
        result = dict(
            documents=list(self.documents.values()),
            stops=list(stops.values()),
            routes=routes,
        )
        temporary = ROOT / "collected.json.tmp"
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        temporary.replace(ROOT / "collected.json")
        return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    data = Collector(args.refresh).run()
    print(
        f"{len(data['stops'])} paradas; {len(data['routes'])} variantes; {len(data['documents'])} documentos"
    )
