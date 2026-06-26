import json
import sys
from pathlib import Path
from image_metadata import read_tags, write_tags, IMAGE_EXTENSIONS, resolve_targets


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


def load_backup(path):
    if not path.exists():
        print(f'Error: backup file not found: {path}')
        return None

    try:
        raw = json.loads(path.read_text('utf-8'))
    except json.JSONDecodeError as e:
        print(f'Error: invalid JSON in {path.name}: {e}')
        return None

    if isinstance(raw, list):
        return {entry['path']: set(entry['tags']) for entry in raw}
    elif isinstance(raw, dict) and 'files' in raw:
        return {p: set(t) for p, t in raw['files'].items()}
    else:
        print('Error: unknown backup format (expected list of {path, tags} or {files: ...})')
        return None


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

    backup = load_backup(backup_file)
    if backup is None:
        sys.exit(1)

    if positional:
        targets = resolve_targets(positional)
        if not targets:
            print('No valid targets found.')
            return
    else:
        targets = [Path.cwd()]
    images = collect_images(targets, recursive=recursive, exclude=exclude)
    if not images:
        print('No supported image files found.')
        return

    matched = 0
    for path in images:
        try:
            rel = path.resolve().relative_to(Path.cwd()).as_posix()
        except ValueError:
            rel = path.name

        backup_tags = backup.get(rel)
        if backup_tags is not None:
            pass
        else:
            matching = {k: v for k, v in backup.items() if Path(k).name == path.name}
            if len(matching) == 1:
                backup_tags = next(iter(matching.values()))
            else:
                continue

        if append:
            existing = read_tags(path)
            merged = existing | backup_tags
            write_tags(path, merged)
        else:
            write_tags(path, backup_tags)

        matched += 1

        action = 'appended' if append else 'written'
        print(f'{path.name}: {len(backup_tags)} tags {action}')

    if matched == 0:
        print('No matching files found in backup.')
        return

    print(f'\nRestored tags to {matched} files.')


if __name__ == '__main__':
    main()
