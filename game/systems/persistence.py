"""Small resilient per-user record store; never writes into source files."""
import json
import os
from pathlib import Path


def record_path():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share'))
    return base / 'Nocturne' / 'record.json'


def load_record():
    try:
        data = json.loads(record_path().read_text(encoding='utf-8'))
        return max(0, int(data.get('high_score', 0)))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def save_record(score):
    try:
        path = record_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'high_score': int(score)}), encoding='utf-8')
        temporary.replace(path)
        return True
    except OSError:
        return False
