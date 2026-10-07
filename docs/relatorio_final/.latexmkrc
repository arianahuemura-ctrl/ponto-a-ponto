# LuaLaTeX permite utilizar Arial instalada no sistema.
$pdf_mode = 4;

# Copia o original sem recompressão quando ele atende ao limite de envio.
# latexmk é executado nesta pasta ou com -cd para o arquivo principal.
$success_cmd = 'python3 gerar_pdf_envio.py';
