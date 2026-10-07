"""Publica o PDF sem perda de qualidade, respeitando o limite de envio."""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
original = BASE / "relatorio_final_pi2.pdf"
destino = BASE / "relatorio_final_pi2_envio.pdf"
limite = 10_000_000  # Limite decimal: também atende a portais que aceitam 10 MiB.
tamanho = original.stat().st_size
if tamanho >= limite:
    destino.unlink(missing_ok=True)
    raise SystemExit(
        f"PDF original com {tamanho:,} bytes: excede o limite de envio. "
        "Ajuste as imagens antes de gerar uma nova versão; o original foi preservado."
    )
shutil.copyfile(original, destino)
print(f"PDF de envio sem perda de qualidade: {tamanho:,} bytes (< 10 MB).")
