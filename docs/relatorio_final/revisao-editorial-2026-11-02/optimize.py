from pathlib import Path
import pikepdf,json
r=Path('/home/avale/Projetos/maua_bus_map-relatorio');c=r/'.cache/setup/editorial-20261102';src=c/'build/relatorio_final_pi2_v2.pdf';out=c/'optimized-qpdf.pdf'
pikepdf.settings.set_flate_compression_level(9)
with pikepdf.open(src) as pdf:
 pdf.remove_unreferenced_resources()
 pdf.save(out,compress_streams=True,recompress_flate=True,object_stream_mode=pikepdf.ObjectStreamMode.generate)
print(json.dumps({'compiled_bytes':src.stat().st_size,'optimized_bytes':out.stat().st_size,'method':'pikepdf/qpdf lossless Flate recompression level 9, object streams, remove unreferenced resources; no rasterization/resampling'},indent=2))
