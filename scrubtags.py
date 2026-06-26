import sys
import re
from pathlib import Path
from image_metadata import read_tags, replace_xmp, build_xmp, IMAGE_EXTENSIONS, resolve_targets


def is_suspicious(tag):
    if not tag or not tag.strip():
        return True

    s = tag.strip()

    try:
        float(s)
        return True
    except ValueError:
        pass

    if ',' in s and any(c.isdigit() for c in s):
        return True

    if ';' in s and any(c.isdigit() for c in s):
        return True

    tokens = s.split()
    numeric = 0
    for t in tokens:
        try:
            float(t.rstrip(',;.:'))
            numeric += 1
        except ValueError:
            pass
    if numeric >= 2:
        return True

    return False


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
        elif a.startswith('-'):
            flags.setdefault('bool', set()).add(a)
            i += 1
        else:
            positional.append(Path(a))
            i += 1

    bool_flags = flags.get('bool', set())
    clean = '--clean' in bool_flags
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

    all_suspicious = {}
    total_clean = 0

    for path in images:
        tags = read_tags(path)
        suspicious = {t for t in tags if is_suspicious(t)}
        clean_tags = tags - suspicious

        if suspicious:
            all_suspicious[path] = suspicious
            total_clean += len(suspicious)
            plural = 's' if len(suspicious) > 1 else ''
            print(f'{path.name}: {len(suspicious)} suspicious tag{plural}')

            if clean:
                if clean_tags:
                    xmp = build_xmp(clean_tags)
                    replace_xmp(path, xmp)
                else:
                    replace_xmp(path, None)
                print(f'         -> {len(clean_tags)} tags kept')
        else:
            print(f'{path.name}: clean')

    print()

    if not all_suspicious:
        print('No suspicious tags found.')
        return

    if not clean:
        print(f'Found {total_clean} suspicious tags across {len(all_suspicious)} files.')
        print('Pass --clean to remove them.')
        print()
        print('Suspicious tags found:')
        seen = set()
        for susp in all_suspicious.values():
            seen.update(susp)
        for t in sorted(seen):
            print(f'  {repr(t)}')
    else:
        print(f'Cleaned {total_clean} suspicious tags from {len(all_suspicious)} files.')

    print('\nDone.')


if __name__ == '__main__':
    main()
