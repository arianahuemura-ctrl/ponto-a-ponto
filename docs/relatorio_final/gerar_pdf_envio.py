"""Prepara, sem recompressão, a versão de envio do PDF efetivamente compilado."""
from pathlib import Path
import argparse
import shutil


def preparar(original: Path) -> Path | None:
    destino = original.with_name(original.stem + "_envio.pdf")
    limite = 10_000_000
    tamanho = original.stat().st_size
    if tamanho >= limite:
        destino.unlink(missing_ok=True)
        print(
            f"PDF compilado preservado: {original.name} ({tamanho:,} bytes). "
            "Versão de envio abaixo de 10 MB não gerada; é necessário otimizar as imagens."
        )
        return None
    shutil.copyfile(original, destino)
    print(f"PDF de envio: {destino.name}, {tamanho:,} bytes (< 10 MB).")
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", nargs="?", type=Path,
                        default=Path(__file__).resolve().parent / "relatorio_final_pi2.pdf")
    preparar(parser.parse_args().original.resolve())
