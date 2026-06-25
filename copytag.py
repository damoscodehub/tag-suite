import sys
from pathlib import Path
from image_metadata import read_tags, write_tags, IMAGE_EXTENSIONS


def collect_targets(args, recursive=False):
    files = []
    for a in args:
        if not a.exists():
            print(f'Skipping (not found): {a}')
            continue
        if a.is_file():
            if a.suffix.lower() in IMAGE_EXTENSIONS:
                files.append(a)
            else:
                print(f'Skipping (unsupported format): {a}')
        else:
            it = a.rglob('*') if recursive else a.iterdir()
            found = sorted([p for p in it if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS])
            files.extend(found)
    return sorted(set(files))


def main():
    raw_args = sys.argv[1:]

    if not raw_args:
        print('Usage: copytag source target1 [target2 ...] [--overwrite]')
        sys.exit(1)

    flags = {a for a in raw_args if a.startswith('-')}
    paths = [Path(a) for a in raw_args if not a.startswith('-')]

    if len(paths) < 2:
        print('Error: need at least a source and one target.')
        sys.exit(1)

    source = paths[0]
    if not source.is_file():
        print(f'Error: source must be a file, got: {source}')
        sys.exit(1)

    source_tags = read_tags(source)
    if not source_tags:
        print(f'No tags found in source: {source.name}')
        sys.exit(1)

    overwrite = '--overwrite' in flags
    recursive = '--recursive' in flags or '-r' in flags
    targets = collect_targets(paths[1:], recursive=recursive)
    if not targets:
        print('No valid target files.')
        return

    for t in targets:
        if overwrite:
            target_tags = set()
        else:
            target_tags = read_tags(t)
            existing_count = len(target_tags)

        merged = source_tags | target_tags
        added = len(merged) - len(target_tags)

        write_tags(t, merged)

        parts = [t.name]
        if not overwrite and existing_count:
            parts.append(f'{existing_count} existing')
        if overwrite:
            parts.append(f'overwritten => {len(merged)}')
        else:
            parts.append(f'+{added} new => {len(merged)}')
        print(', '.join(parts))

    print('\nDone.')


if __name__ == '__main__':
    main()
