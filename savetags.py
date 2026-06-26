import json
import sys
import re
from pathlib import Path
from image_metadata import read_tags, IMAGE_EXTENSIONS, resolve_targets


DEFAULT_BACKUP = Path('tags_backup.json')


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


def find_sequence_max(base):
    stem = base.stem
    suffix = base.suffix
    parent = base.parent
    pattern = re.compile(re.escape(stem) + r'\((\d+)\)' + re.escape(suffix) + '$')
    max_n = 0
    if base.exists():
        max_n = 0
    for p in parent.iterdir():
        m = pattern.match(p.name)
        if m:
            n = int(m.group(1))
            if n > max_n:
                max_n = n
    return max_n


def next_sequence_path(base):
    max_n = find_sequence_max(base)
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    parent = base.parent
    return parent / f'{stem}({max_n + 1}){suffix}'


def prompt_mode(base):
    print(f'{base.name} already exists.')
    while True:
        choice = input('[N] Auto-sequence  [RN] Rename new  [RO] Rename old  [OW] Overwrite  [A] Append\nChoose: ').strip().lower()
        if choice in ('n', 'autosequence', 'auto'):
            return 'sequencenew'
        elif choice in ('rn', 'renamenew'):
            return 'renamenew'
        elif choice in ('ro', 'renameold'):
            return 'renameold'
        elif choice in ('ow', 'overwrite'):
            return 'overwrite'
        elif choice in ('a', 'append'):
            return 'append'


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
        elif a in ('--output', '-o') and i + 1 < len(raw):
            flags['output'] = Path(raw[i + 1])
            i += 2
        elif a.startswith('-'):
            flags.setdefault('bool', set()).add(a)
            i += 1
        else:
            positional.append(Path(a))
            i += 1

    bool_flags = flags.get('bool', set())
    base = flags.get('output', DEFAULT_BACKUP)

    mode = None
    if '--overwrite' in bool_flags or '-ow' in bool_flags:
        mode = 'overwrite'
    elif '--append' in bool_flags or '-a' in bool_flags:
        mode = 'append'
    elif '--sequencenew' in bool_flags or '-s' in bool_flags:
        mode = 'sequencenew'
    elif '--renamenew' in bool_flags or '-rn' in bool_flags:
        mode = 'renamenew'
    elif '--renameold' in bool_flags or '-ro' in bool_flags:
        mode = 'renameold'

    recursive = '--recursive' in bool_flags or '-r' in bool_flags
    exclude = flags.get('exclude')

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

    if mode is None and base.exists():
        mode = prompt_mode(base)

    if mode is None:
        backup_file = base
    elif mode == 'overwrite':
        backup_file = base
    elif mode == 'append':
        backup_file = base
    elif mode == 'sequencenew':
        backup_file = next_sequence_path(base)
    elif mode == 'renamenew':
        new_name = input(f'New filename (default: {base.name}): ').strip()
        backup_file = base.with_name(new_name) if new_name else base
    elif mode == 'renameold':
        new_name = input(f'Rename existing {base.name} to: ').strip()
        if not new_name:
            print('Cannot rename to empty name.')
            sys.exit(1)
        old_path = base.with_name(new_name)
        base.rename(old_path)
        print(f'Renamed to {old_path.name}')
        backup_file = base
    else:
        backup_file = base

    mode_str = mode or 'default'
    use_append = mode == 'append'

    backup = {}
    if use_append and backup_file.exists():
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
