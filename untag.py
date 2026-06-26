import sys
from pathlib import Path
from image_metadata import read_tags, replace_xmp, build_xmp, IMAGE_EXTENSIONS, resolve_targets


def collect_files(targets, recursive=False):
    files = []
    for t in targets:
        if not t.exists():
            print(f'Skipping (not found): {t}')
            continue
        if t.is_file():
            if t.suffix.lower() in IMAGE_EXTENSIONS:
                files.append(t)
            else:
                print(f'Skipping (unsupported format): {t}')
        else:
            it = t.rglob('*') if recursive else t.iterdir()
            found = sorted([p for p in it if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS])
            files.extend(found)
    return sorted(set(files))


def parse_tag_list(raw):
    return {t.strip() for t in raw.split(',') if t.strip()}


def main():
    raw_args = sys.argv[1:]

    flags = {}
    positional = []
    recursive = False
    i = 0
    while i < len(raw_args):
        a = raw_args[i]
        if a in ('-r', '--recursive'):
            recursive = True
            i += 1
        elif a == '--tags' and i + 1 < len(raw_args):
            flags['tags'] = parse_tag_list(raw_args[i + 1])
            i += 2
        elif a == '--preserve' and i + 1 < len(raw_args):
            flags['preserve'] = parse_tag_list(raw_args[i + 1])
            i += 2
        elif a.startswith('-'):
            i += 1
        else:
            positional.append(Path(a))
            i += 1

    if positional:
        targets = resolve_targets(positional)
        if not targets:
            print('No valid targets found.')
            return
    else:
        targets = [Path.cwd()]
    files = collect_files(targets, recursive=recursive)

    tags_to_remove = flags.get('tags')
    tags_to_preserve = flags.get('preserve')

    for f in files:
        existing = read_tags(f)

        if not existing:
            print(f'No tags found in {f.name}')
            continue

        if tags_to_remove is not None and tags_to_preserve is not None:
            remaining = (existing - tags_to_remove) | (existing & tags_to_preserve)
        elif tags_to_remove is not None:
            remaining = existing - tags_to_remove
        elif tags_to_preserve is not None:
            remaining = existing & tags_to_preserve
        else:
            remaining = set()

        removed = existing - remaining
        if not removed:
            print(f'No matching tags to remove in {f.name}')
            continue

        old_size = f.stat().st_size
        xmp_data = build_xmp(remaining) if remaining else None
        replace_xmp(f, xmp_data)
        new_size = f.stat().st_size

        kept = len(remaining)
        total = len(existing)
        action = f'Removed {len(removed)}/{total} tags'
        if kept:
            action += f', kept {kept}'
        print(f'{f.name}: {action} ({old_size - new_size:,}B)')

    print('\nDone.')


if __name__ == '__main__':
    main()
