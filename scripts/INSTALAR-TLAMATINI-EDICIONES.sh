#!/usr/bin/env bash
set -euo pipefail
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Preparando Python 3 para descargar y verificar el instalador...'
  if [ "$(id -u)" -eq 0 ]; then
    apt-get update && apt-get install -y python3
  else
    sudo apt-get update && sudo apt-get install -y python3
  fi
fi
exec python3 - "$@" <<'PYTHON'
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request

CATALOG_URL = 'https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/download/ediciones-2026-11-13/INSTALADORES-SEIS-EDICIONES.json'
BLOCK = 1024 * 1024


def valid_file(path, expected):
    if not path.is_file() or path.stat().st_size != expected['size_bytes']:
        return False
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(BLOCK), b''):
            digest.update(chunk)
    return digest.hexdigest() == expected['sha256']


def download_file(item, path):
    if valid_file(path, item):
        print('Ya descargado y verificado:', path.name, flush=True)
        return
    temporary = path.with_name(path.name + '.download')
    digest = hashlib.sha256()
    count = 0
    request = urllib.request.Request(item['url'], headers={'User-Agent': 'TLAMATINI-Installer'})
    try:
        with urllib.request.urlopen(request, timeout=90) as source, temporary.open('wb') as output:
            while chunk := source.read(BLOCK):
                count += len(chunk)
                if count > item['size_bytes']:
                    raise RuntimeError('El archivo recibido es mayor de lo esperado.')
                output.write(chunk)
                digest.update(chunk)
        if count != item['size_bytes'] or digest.hexdigest() != item['sha256']:
            raise RuntimeError('La descarga no pasó la verificación SHA-256: ' + path.name)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def assemble_files(paths, output, expected):
    if valid_file(output, expected):
        return
    temporary = output.with_name(output.name + '.assembling')
    digest = hashlib.sha256()
    count = 0
    try:
        with temporary.open('wb') as target:
            for path in paths:
                with path.open('rb') as source:
                    while chunk := source.read(BLOCK):
                        target.write(chunk)
                        count += len(chunk)
                        digest.update(chunk)
        if count != expected['size_bytes'] or digest.hexdigest() != expected['sha256']:
            raise RuntimeError('El instalador unido no pasó la verificación SHA-256.')
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def read_catalog(location):
    if location.startswith('https://'):
        with urllib.request.urlopen(location, timeout=30) as response:
            return json.load(response)
    return json.loads(Path(location).read_text(encoding='utf-8'))


def select_edition(catalog, edition):
    if catalog.get('schema_version') != 1:
        raise RuntimeError('El catálogo de instalación no es compatible.')
    item = catalog['editions']['linux-' + edition]
    if item.get('platform') != 'linux' or not item['filename'].endswith('.deb'):
        raise RuntimeError('El catálogo no corresponde a Linux.')
    for name in [item['filename']] + [p['name'] for p in item['downloads']]:
        if Path(name).name != name or name in ('.', '..'):
            raise RuntimeError('Nombre de archivo inválido en el catálogo.')
    if not item['downloads'] or sum(p['size_bytes'] for p in item['downloads']) != item['size_bytes']:
        raise RuntimeError('La lista de descargas está incompleta.')
    return item


def main():
    parser = argparse.ArgumentParser(description='Instala una edición de TLAMATINI en Linux de 64 bits.')
    parser.add_argument('edicion', choices=['sin-ia', 'ia-4gb', 'ia-8gb'])
    parser.add_argument('--catalogo', default=CATALOG_URL)
    parser.add_argument('--carpeta', type=Path)
    parser.add_argument('--solo-descargar', action='store_true')
    parser.add_argument('--verificar', action='store_true')
    args = parser.parse_args()
    item = select_edition(read_catalog(args.catalogo), args.edicion)
    print('TLAMATINI', item['version'], '| Linux 64 bits |', item['model'] or 'Sin IA', flush=True)
    if item['ram_recommended_gib']:
        print('RAM recomendada:', item['ram_recommended_gib'], 'GB', flush=True)
    if args.verificar:
        print('Catálogo verificado:', len(item['downloads']), 'archivo(s);', item['size_bytes'], 'bytes.')
        return 0
    if platform.machine().lower() not in ('x86_64', 'amd64'):
        raise RuntimeError('Esta edición necesita Linux de 64 bits amd64/x86_64.')
    if not shutil.which('apt'):
        raise RuntimeError('Usa este instalador en Debian, Ubuntu o Linux Mint con apt.')
    folder = args.carpeta or Path.home() / 'Downloads' / 'TLAMATINI' / args.edicion
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / item['filename']
    if not valid_file(output, item):
        if len(item['downloads']) == 1:
            download_file(item['downloads'][0], output)
        else:
            parts_dir = folder / '_partes'
            parts_dir.mkdir(exist_ok=True)
            paths = []
            for number, part in enumerate(item['downloads'], 1):
                print(f'Descargando {number}/{len(item["downloads"])}...', flush=True)
                path = parts_dir / part['name']
                download_file(part, path)
                paths.append(path)
            print('Preparando el instalador completo...', flush=True)
            assemble_files(paths, output, item)
    if len(item['downloads']) > 1:
        parts_dir = folder / '_partes'
        for part in item['downloads']:
            (parts_dir / part['name']).unlink(missing_ok=True)
        try:
            parts_dir.rmdir()
        except OSError:
            pass
    print('Instalador completo y verificado:', output, flush=True)
    if not args.solo_descargar:
        command = ['apt', 'install', '-y', str(output.resolve())]
        if os.geteuid() != 0:
            command.insert(0, 'sudo')
        subprocess.run(command, check=True)
        print('Instalación terminada. Abre TLAMATINI desde el menú de aplicaciones o escribe: tlamatini')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print('Error:', error, file=sys.stderr)
        print('Vuelve a ejecutar el mismo comando para reanudar los archivos ya verificados.', file=sys.stderr)
        raise SystemExit(1)
PYTHON
