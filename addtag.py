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


def parse_tag_list(raw):
    return {t.strip() for t in raw.split(',') if t.strip()}


def read_tags_file(path):
    try:
        lines = [l.strip().strip('"') for l in Path(path).read_text('utf-8').splitlines() if l.strip()]
        return {t for t in lines if t}
    except Exception as e:
        print(f'Error reading tags file {path}: {e}')
        return set()


def prompt_tags():
    print('Enter tags (comma-separated):')
    raw = input().strip()
    if raw:
        return parse_tag_list(raw)
    return set()


def main():
    raw = sys.argv[1:]

    tags = set()
    tag_flag_used = False
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
        elif a in ('-ow', '--overwrite'):
            flags['overwrite'] = True
            i += 1
        elif a in ('-a', '--append'):
            flags['mode'] = 'append'
            i += 1
        elif a == '--tags' and i + 1 < len(raw):
            tags.update(parse_tag_list(raw[i + 1]))
            tag_flag_used = True
            i += 2
        elif a == '--tags_file' and i + 1 < len(raw):
            tags.update(read_tags_file(raw[i + 1]))
            tag_flag_used = True
            i += 2
        elif a.startswith('-'):
            i += 1
        else:
            positional.append(Path(a))
            i += 1

    if not tags and not tag_flag_used:
        tags = prompt_tags()
        if not tags:
            print('No tags provided.')
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

    overwrite = flags.get('overwrite', False)

    for path in images:
        if overwrite:
            current = set()
        else:
            current = read_tags(path)

        merged = tags | current
        added = len(merged) - len(current)

        write_tags(path, merged)

        parts = [path.name]
        if overwrite:
            parts.append(f'overwritten => {len(merged)}')
        else:
            parts.append(f'+{added} new => {len(merged)}')
        print(', '.join(parts))

    print('\nDone.')


if __name__ == '__main__':
    main()
