import json
import sys
from pathlib import Path
from image_metadata import read_tags, IMAGE_EXTENSIONS


BACKUP_FILE = Path('tags_backup.json')


def collect_images(targets, recursive=False, exclude=None):
    images = []
    for t in targets:
        if not t.exists():
            print(f'Skipping (not found): {t}')
            continue
        if t.is_file():
            if t.suffix.lower() in IMAGE_EXTENSIONS:
                if exclude and any(t.match(p) for p in exclude):
                    print(f'Skipping (excluded): {t.name}')
                    continue
                images.append(t)
            else:
                print(f'Skipping (unsupported format): {t}')
        else:
            it = t.rglob('*') if recursive else t.iterdir()
            found = sorted([p for p in it if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS])
            if exclude:
                found = [p for p in found if not any(p.match(pat) for pat in exclude)]
            images.extend(found)
    return sorted(set(images))


def main():
    raw = sys.argv[1:]

    flags = {}
    positional = []
    i = 0
    while i < len(raw):
        a = raw[i]
        if a == '--exclude' and i + 1 < len(raw):
            flags['exclude'] = [p.strip() for p in raw[i + 1].split(',') if p.strip()]
            i += 2
        elif a in ('--backup', '-b') and i + 1 < len(raw):
            flags['backup'] = Path(raw[i + 1])
            i += 2
        elif a.startswith('-'):
            flags.setdefault('bool', set()).add(a)
            i += 1
        else:
            positional.append(Path(a))
            i += 1

    bool_flags = flags.get('bool', set())
    append = '--append' in bool_flags or '-a' in bool_flags
    recursive = '--recursive' in bool_flags or '-r' in bool_flags
    exclude = flags.get('exclude')
    backup_file = flags.get('backup', BACKUP_FILE)

    targets = positional or [Path.cwd()]
    images = collect_images(targets, recursive=recursive, exclude=exclude)
    if not images:
        print('No supported image files found.')
        return

    backup = {}
    if append and backup_file.exists():
        try:
            existing = json.loads(backup_file.read_text('utf-8'))
            if isinstance(existing, list):
                for entry in existing:
                    backup[entry['path']] = set(entry['tags'])
            elif isinstance(existing, dict) and 'files' in existing:
                for p, t in existing['files'].items():
                    backup[p] = set(t)
            print(f'Loaded {len(backup)} existing entries from {backup_file.name}')
        except (json.JSONDecodeError, KeyError):
            print(f'Warning: could not parse {backup_file.name}, starting fresh.')
            backup = {}

    for path in images:
        tags = read_tags(path)
        rel = path.resolve().relative_to(Path.cwd()).as_posix()
        backup[rel] = tags

    output = [{'path': p, 'tags': sorted(t)} for p, t in sorted(backup.items())]
    backup_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), 'utf-8')
    print(f'Saved {len(output)} file entries to {backup_file.name}')

    print('\nDone.')


if __name__ == '__main__':
    main()
