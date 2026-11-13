"""Export every authored code file, by path, for a complete reviewable delivery."""
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    paths = [root/'main.py', root/'Jugar.cmd', root/'requirements.txt']
    paths += sorted((root/'game').rglob('*.py'))
    paths += sorted((root/'tests').rglob('*.py'))
    paths += sorted((root/'tools').glob('*.py'))
    sections = [
        '# NOCTURNE — Código completo por archivo\n',
        'Dependencia: `panda3d==1.10.16`; Python 3.10+. '
        'Consulta README.md para la función de cada módulo y las instrucciones de ejecución y pruebas.\n',
    ]
    for path in paths:
        relative=path.relative_to(root).as_posix()
        language='python' if path.suffix=='.py' else 'bat' if path.suffix=='.cmd' else 'text'
        sections.append(f'## {relative}\n\nRuta: `{relative}`\n\n```{language}\n{path.read_text(encoding="utf-8").rstrip()}\n```\n')
    output=root/'CODIGO_COMPLETO.md'
    output.write_text('\n'.join(sections),encoding='utf-8')
    print(f'{len(paths)} archivos exportados a {output}')


if __name__=='__main__':
    main()
