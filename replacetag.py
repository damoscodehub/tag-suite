import sys
from pathlib import Path
from image_metadata import read_tags, write_tags, IMAGE_EXTENSIONS, resolve_targets


def collect_files(targets, recursive=False, exclude=None):
    files = []
    for t in targets:
        if not t.exists():
            print(f'Skipping (not found): {t}')
            continue
        if t.is_file():
            if t.suffix.lower() in IMAGE_EXTENSIONS:
                if exclude and any(t.match(p) for p in exclude):
                    print(f'Skipping (excluded): {t.name}')
                    continue
                files.append(t)
            else:
                print(f'Skipping (unsupported format): {t}')
        else:
            it = t.rglob('*') if recursive else t.iterdir()
            found = sorted([p for p in it if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS])
            if exclude:
                found = [p for p in found if not any(p.match(pat) for pat in exclude)]
            files.extend(found)
    return sorted(set(files))


def parse_replacements(raw):
    result = {}
    for pair in raw.split(','):
        pair = pair.strip()
        if not pair:
            continue
        if '=' in pair:
            old, new = pair.split('=', 1)
            old, new = old.strip(), new.strip()
            if old and old != new:
                result[old] = new
        else:
            if pair:
                result[pair] = ''
    return result


def read_replacements_file(path):
    result = {}
    try:
        lines = [l.strip().strip('"') for l in Path(path).read_text('utf-8').splitlines() if l.strip()]
        for line in lines:
            if '=' in line:
                old, new = line.split('=', 1)
                old, new = old.strip(), new.strip()
                if old and old != new:
                    result[old] = new
            else:
                if line:
                    result[line] = ''
    except Exception as e:
        print(f'Error reading replacements file {path}: {e}')
    return result


def prompt_replacements():
    print('Enter replacements (old=new, comma-separated):')
    raw = input().strip()
    if raw:
        return parse_replacements(raw)
    return {}


def apply_replacements(tags, replacements):
    result = set(tags)
    for old, new in replacements.items():
        if old in result:
            result.discard(old)
            if new:
                result.add(new)
    return result


def main():
    raw = sys.argv[1:]

    replacements = {}
    flag_used = False
    flags = {}
    positional = []
    i = 0
    while i < len(raw):
        a = raw[i]
        if a in ('-r', '--recursive'):
            flags['recursive'] = True
            i += 1
        elif a == '--exclude' and i + 1 < len(raw):
            flags['exclude'] = [p.strip() for p in raw[i + 1].split(',') if p.strip()]
            i += 2
        elif a == '--tags' and i + 1 < len(raw):
            replacements.update(parse_replacements(raw[i + 1]))
            flag_used = True
            i += 2
        elif a == '--tags_file' and i + 1 < len(raw):
            replacements.update(read_replacements_file(raw[i + 1]))
            flag_used = True
            i += 2
        elif a.startswith('-'):
            i += 1
        else:
            positional.append(Path(a))
            i += 1

    if not replacements and not flag_used:
        replacements = prompt_replacements()
        if not replacements:
            print('No replacements provided.')
            sys.exit(1)

    if positional:
        targets = resolve_targets(positional)
        if not targets:
            print('No valid targets found.')
            return
    else:
        targets = [Path.cwd()]

    images = collect_files(targets, recursive=flags.get('recursive', False), exclude=flags.get('exclude'))
    if not images:
        print('No supported image files found.')
        return

    for path in images:
        current = read_tags(path)
        if not current:
            print(f'{path.name}: no tags')
            continue

        replaced = apply_replacements(current, replacements)
        changed = replaced != current

        if not changed:
            print(f'{path.name}: no matches')
            continue

        write_tags(path, replaced)

        removed = current - replaced
        added = replaced - current
        parts = [path.name]
        if removed:
            parts.append(f'-{len(removed)}')
        if added:
            parts.append(f'+{len(added)}')
        parts.append(f'=> {len(replaced)}')
        print(', '.join(parts))

    print('\nDone.')


if __name__ == '__main__':
    main()
