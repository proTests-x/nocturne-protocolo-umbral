"""Launch NOCTURNE from any working directory. See README.md for controls."""
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description='NOCTURNE | Protocolo Umbral')
    parser.add_argument('--quality', choices=('low', 'medium', 'high'), default='medium')
    parser.add_argument('--mute', action='store_true', help='Desactivar audio')
    parser.add_argument('--seed', type=int, default=None, help='Semilla reproducible')
    parser.add_argument('--smoke-test', action='store_true', help='Ejecutar combate automatizado y salir')
    parser.add_argument('--offscreen', action='store_true', help='Renderizar sin ventana')
    parser.add_argument('--frames', type=int, default=900, help='Duracion de smoke-test en fotogramas')
    parser.add_argument('--screenshot', type=Path, help='Guardar captura PNG al final de smoke-test')
    parser.add_argument('--menu-screenshot', type=Path, help='Guardar captura del menu y salir')
    args = parser.parse_args()
    if args.frames < 1:
        parser.error('--frames debe ser positivo')
    try:
        from panda3d.core import loadPrcFileData
    except ImportError:
        print('Falta Panda3D. Instala con: python -m pip install -r requirements.txt', file=sys.stderr)
        return 1
    settings = '\n'.join([
        'window-title NOCTURNE | Protocolo Umbral', 'win-size 1280 720',
        'win-origin -2 -2', 'sync-video true', 'show-frame-rate-meter false',
        'framebuffer-multisample true', 'multisamples 2', 'audio-library-name p3openal_audio',
        'notify-level warning', 'default-directnotify-level warning',
        'textures-power-2 none', 'cursor-hidden false', 'gl-check-errors false',
    ])
    if args.offscreen:
        settings += '\nwindow-type offscreen'
    if args.mute:
        settings += '\naudio-library-name null'
    if args.smoke_test or args.menu_screenshot:
        settings += '\nsync-video false'
    loadPrcFileData('nocturne', settings)
    from game.app import NocturneApp
    app = NocturneApp(args)
    try:
        app.run()
    except KeyboardInterrupt:
        app.quit_game()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
