"""Create a portable source package without the machine-specific environment."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import export_source


def main():
    export_source.main()
    root=Path(__file__).resolve().parents[1]
    output=root/'Nocturne-prototipo.zip'
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        paths=[root/name for name in ('main.py','Jugar.cmd','requirements.txt','README.md','VERIFICACION.md','CODIGO_COMPLETO.md','.gitignore')]
        for directory in ('game','tests','tools'):
            paths.extend(p for p in (root/directory).rglob('*')
                         if p.is_file() and '__pycache__' not in p.parts
                         and 'generated' not in p.parts and p.suffix in ('.py','.md','.wav'))
        for path in paths:
            archive.write(path,'Nocturne/'+path.relative_to(root).as_posix())
    print(f'{output.name}: {output.stat().st_size:,} bytes; {len(paths)} archivos')


if __name__=='__main__':
    main()
