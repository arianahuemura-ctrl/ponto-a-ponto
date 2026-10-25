from pathlib import Path
import zipfile,copy
from lxml import etree as E
src=(Path(__file__).resolve().parent/'modelo_termo.docx');out=(Path(__file__).resolve().parent/'Termo_autorizacao_Alameda_Solutions.docx')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+ns['w']+'}'
with zipfile.ZipFile(src) as z:
 root=E.fromstring(z.read('word/document.xml'));ps=root.findall('.//w:p',ns)
 def setp(i,text):
  p=ps[i];runs=p.findall('w:r',ns);style=copy.deepcopy(runs[0].find('w:rPr',ns)) if runs and runs[0].find('w:rPr',ns) is not None else None
  for c in list(p):
   if c.tag!=W+'pPr':p.remove(c)
  r=E.SubElement(p,W+'r')
  if style is not None:r.append(style)
  E.SubElement(r,W+'t').text=text
 setp(1,'Como responsável pela empresa/instituição Alameda Solutions, CNPJ 60.184.290/0001-00, autorizo a realização do trabalho realizado pelo(s) aluno(s) da Universidade Virtual do Estado de São Paulo (Univesp), a seguir discriminado(s):')
 setp(4,'(  X  ) Projeto Integrador')
 setp(5,'Título do trabalho: Sistema de acesso a informações do transporte público por QR Code em pontos de ônibus (Ponto a Ponto).')
 for i,t in enumerate(['André Meneghelli Vale; Ariana Harumi Uemura;', 'Bruno Gabriel Migliari de Souza; Caio Wellington Procopio Ferreira;', 'Ingrid Emanuelle Sousa Dias; Leonardo Souza Leite;', 'Maurício Gonçalves Marques; Nathalia Almeida Amorim.'],7):setp(i,t)
 setp(12,'Desenvolver e analisar um protótipo web de acesso a informações do transporte público por QR Code em pontos de ônibus, apoiando a identificação da origem, a consulta de linhas e a escolha de alternativas de viagem.')
 setp(13,'Investigar a clareza das informações e a facilidade de uso da solução, documentando os procedimentos e resultados para fins acadêmicos.')
 setp(14,'Verificações da Alameda Solutions: primeiro feedback em 21/10/2026 e atualização em 25/10/2026, sobre as modificações realizadas até cada data.')
 setp(36,'Nome: Thiago Almeida Amorim')
 for i in [2,15,16,22,24,26,27,29,30,31,32,35]:ps[i].getparent().remove(ps[i])
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dst:
  for item in z.infolist():dst.writestr(item,E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
print(out)
