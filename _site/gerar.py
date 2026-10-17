"""Gera os dados do site da Central de Materiais.
Roda na pasta "Central de Materiais - Planeta Água":
  python3 _site/gerar.py
- Lê as pastas 01..05 e monta _site/dados.js
- Cria miniaturas (_site/mini) e versões leves para WhatsApp (_site/leve)
- Só refaz o que mudou (pode rodar várias vezes)."""
import os, sys, json, hashlib, subprocess, time, unicodedata
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(RAIZ, '_site')
SECOES = ['01 - Tabelas de Preços', '02 - Fabricantes', '03 - Produtos', '04 - Divulgação', '05 - Vendas e Treinamento']
IMG = ('.png', '.jpg', '.jpeg', '.webp')
LIMITE = float(sys.argv[1]) if len(sys.argv) > 1 else 1e9   # segundos de trabalho pesado nesta rodada
inicio = time.time()

def nfc(s): return unicodedata.normalize('NFC', s)
def chave(rel): return hashlib.md5(rel.encode('utf-8')).hexdigest()[:12]

def precisa(src, dst):
    return not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src)

def achatar(im):
    im = ImageOps.exif_transpose(im)
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA'); fundo = Image.new('RGB', im.size, (255, 255, 255))
        fundo.paste(im, mask=im.split()[-1]); return fundo
    return im.convert('RGB')

def reduzir(im, lado):
    f = max(im.size) // (lado * 2)
    if f >= 2: im = im.reduce(f)
    im.thumbnail((lado, lado), Image.LANCZOS); return im

pendente = 0
def trabalho():
    return time.time() - inicio < LIMITE

itens = []
for sec in SECOES:
    base = os.path.join(RAIZ, sec)
    for pasta, dirs, arqs in os.walk(base):
        dirs.sort()
        for a in sorted(arqs):
            if a.startswith('.') or a.lower() == 'desktop.ini': continue
            src = os.path.join(pasta, a)
            rel = os.path.relpath(src, RAIZ).replace(os.sep, '/')
            ext = os.path.splitext(a)[1].lower()
            k = chave(rel)
            it = {'id': k, 'arq': nfc(rel), 'nome': nfc(os.path.splitext(a)[0]), 'ext': ext.lstrip('.'),
                  'tam': os.path.getsize(src),
                  'pasta': nfc(os.path.relpath(pasta, base).replace(os.sep, '/')) if pasta != base else '',
                  'sec': nfc(sec)}
            mini = os.path.join(SITE, 'mini', k + '.jpg')
            leve = os.path.join(SITE, 'leve', k + '.jpg')
            try:
                if ext in IMG:
                    if precisa(src, leve) or precisa(src, mini):
                        if trabalho():
                            im = Image.open(src); im.load()
                            f = max(im.size) // 1600
                            if f >= 2:
                                im2 = im.reduce(f); im.close(); im = im2
                            im = achatar(im)
                            l = reduzir(im.copy(), 1600); l.save(leve, 'JPEG', quality=84, optimize=True, progressive=True)
                            m = reduzir(im, 520); m.save(mini, 'JPEG', quality=78, optimize=True, progressive=True)
                            del im, l, m
                        else: pendente += 1
                    if os.path.exists(leve):
                        with Image.open(leve) as l: it['w'], it['h'] = l.size
                        it['leve'] = '_site/leve/' + k + '.jpg'; it['leveTam'] = os.path.getsize(leve)
                elif ext == '.pdf':
                    if precisa(src, mini):
                        if trabalho():
                            tmp = os.path.join(SITE, 'tmp_' + k)
                            subprocess.run(['pdftoppm', '-f', '1', '-l', '1', '-r', '50', '-jpeg', '-singlefile', src, tmp], check=True, timeout=120)
                            im = Image.open(tmp + '.jpg').convert('RGB'); reduzir(im, 520).save(mini, 'JPEG', quality=80)
                            os.remove(tmp + '.jpg')
                        else: pendente += 1
                    try:
                        out = subprocess.run(['pdfinfo', src], capture_output=True, text=True, timeout=30).stdout
                        it['pags'] = int([l for l in out.splitlines() if l.startswith('Pages:')][0].split()[-1])
                    except Exception: pass
                elif ext == '.mp4':
                    if precisa(src, mini):
                        if trabalho():
                            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '1', '-i', src, '-frames:v', '1', '-vf', 'scale=520:-2', mini], check=True, timeout=120)
                        else: pendente += 1
                if os.path.exists(mini): it['mini'] = '_site/mini/' + k + '.jpg'
            except Exception as e:
                print('ERRO', rel, e)
            it['data'] = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(src)))
            itens.append(it)

# limpa miniaturas de arquivos que saíram
vivos = {i['id'] for i in itens}
for d in ('mini', 'leve'):
    for f in os.listdir(os.path.join(SITE, d)):
        if f[:-4] not in vivos: os.remove(os.path.join(SITE, d, f))

with open(os.path.join(SITE, 'dados.js'), 'w', encoding='utf-8') as f:
    f.write('// gerado por _site/gerar.py em ' + time.strftime('%d/%m/%Y %H:%M') + '\n')
    f.write('window.ARQUIVOS = ' + json.dumps(itens, ensure_ascii=False, separators=(',', ':')) + ';\n')
    f.write('window.GERADO = "' + time.strftime('%Y-%m-%d %H:%M') + '";\n')
print(len(itens), 'arquivos ·', pendente, 'imagens ainda por preparar')
