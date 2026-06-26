# tag-suite

Command-line tools for AI image tagging, tag copying, and tag removal.

`joytag` uses the [JoyTag](https://github.com/fpgaminer/joytag) vision model to automatically tag images with 5000+ tags. `copytag` copies tags between files, `addtag` adds tags manually, and `untag` removes tags.

**Supported formats:** JPEG (`.jpg`, `.jpeg`), PNG (`.png`), WebP (`.webp`), TIFF (`.tiff`, `.tif`).

## Setup

Install dependencies:

```bash
pip install torch torchvision Pillow safetensors transformers einops
```

Download the model from [HuggingFace](https://huggingface.co/fancyfeast/joytag/tree/main) and place it in `models/`. The folder must contain `model.safetensors`, `config.json`, and `top_tags.txt`.

For convenience, add this repo's folder to your `PATH` to run the commands from anywhere.

## Usage

All tools accept **`.txt` files as target shortcuts** — each line is treated as a file path. This lets you select files in Explorer (Ctrl+Shift+C), paste the paths into a `.txt`, and pass it to any script.

```bash
python joytag.py mylist.txt
python addtag.py targets.txt --tags "1boy,solo"
python untag.py targets.txt --tags "1boy"
python scrubtags.py paths.txt --clean
```

### Tagging Images

```bash
# Tag all supported images in the current directory
python joytag.py

# Tag all supported images in a specific folder
python joytag.py path/to/images

# Tag a single image
python joytag.py image.jpg

# Tag multiple specific images (any formats)
python joytag.py img1.jpg img2.png img3.webp

# Mix files and folders
python joytag.py img1.jpg path/to/folder

# Overwrite existing tags (instead of merging)
python joytag.py image.png --overwrite

# Recursively process subdirectories
python joytag.py path/to/images --recursive
python joytag.py folder -r
```

By default, folders are scanned **non-recursively** (only direct children). Use `--recursive` / `-r` to process subdirectories.

By default, new tags are **merged** with any existing tags — duplicates are avoided. Use `--overwrite` to replace existing tags with only the predicted ones.

If the repo folder is in your `PATH`:

```bash
joytag                  # tag current directory
joytag folder           # tag a folder
joytag image.png        # tag a single image
joytag folder --recursive
```

### Removing Tags

Strips XMP (keywords) and IPTC metadata from images, leaving image data intact.

```bash
# Remove all tags from all supported images in current directory
python untag.py

# Remove all tags from all supported images in a folder
python untag.py path/to/images

# Remove all tags from a single file
python untag.py image.png

# Remove all tags from multiple targets (files and/or folders)
python untag.py img1.jpg img2.webp
python untag.py img1.png path/to/folder

# Remove only specific tags
python untag.py image.jpg --tags "tag1,tag2,tag3"

# Keep only specific tags, remove everything else
python untag.py image.webp --preserve "tag1,tag2"

# Remove specific tags while preserving others
python untag.py image.png --tags "bad1,bad2" --preserve "good1"

# Recursively process subdirectories
python untag.py path/to/images --recursive

# Via PATH
untag
untag image.jpg --tags "1girl,solo"
untag folder --preserve "photo_(medium)"
```

### Copying Tags

Copies tags from one tagged image to other files without running the model — reads existing tags from the source and writes them to targets.

```bash
# Copy tags from source to one or more targets (any formats)
python copytag.py source.png target1.jpg target2.webp

# Copy tags to all images in a folder
python copytag.py source.jpg path/to/folder

# Mix files and folders as targets
python copytag.py source.png img1.jpg path/to/folder

# Overwrite existing tags on targets (instead of merging)
python copytag.py source.webp target.jpg --overwrite

# Recursively process target subdirectories
python copytag.py source.png path/to/images -r

# Via PATH
copytag source.png target.jpg
copytag source.jpg folder --overwrite
```

By default, source tags are **merged** into targets — duplicates are avoided. Use `--overwrite` to replace all tags on targets with only the source's tags.

### Adding Manually Tags

Add specific tags to images without running the AI model.

```bash
# Add tags to all images in current directory (interactive prompt)
python addtag.py

# Add tags to a specific folder or files
python addtag.py path/to/images --tags "tag1,tag2,tag3"
python addtag.py img1.jpg img2.png --tags "new_tag,another_tag"

# Overwrite all existing tags (default is append)
python addtag.py image.jpg --tags "tag1,tag2" --overwrite
python addtag.py image.png -ow --tags "tag1"

# Read tags from a .txt file (one tag per line)
python addtag.py folder --tags_file mytags.txt

# Use a .txt file as target list
python addtag.py targets.txt --tags "tag1,tag2"

# Recursively scan subdirectories
python addtag.py path/to/images --tags "tag1" -r

# Exclude files matching glob patterns
python addtag.py path --tags "tag1" --exclude "*thumb*"

# Via PATH
addtag
addtag image.jpg --tags "1girl,solo"
addtag folder --tags_file mytags.txt
```

If neither `--tags` nor `--tags_file` is provided, you'll be prompted to enter tags interactively (comma-separated).

| Flag | Short | Description |
|------|-------|-------------|
| `--tags` | | Comma-separated tags to add |
| `--tags_file` | | Read tags from a .txt file (one per line) |
| `--append` | `-a` | Merge tags with existing (default behavior) |
| `--overwrite` | `-ow` | Replace all existing tags with the new ones |
| `--recursive` | `-r` | Process subdirectories |
| `--exclude` | | Glob patterns to exclude (comma-separated) |

### Replacing Tags

Find and replace tags across images. Renames a tag everywhere it appears without affecting other tags.

```bash
# Replace a single tag in current directory (interactive prompt)
python replacetag.py

# Replace tags in a specific folder or files
python replacetag.py path/to/images --tags "old_tag=new_tag"
python replacetag.py img1.jpg img2.png --tags "bad_tag=good_tag,old=new"

# Remove a tag entirely (replace with nothing)
python replacetag.py image.jpg --tags "unwanted_tag="

# Read replacements from a .txt file (one old=new per line)
python replacetag.py folder --tags_file repls.txt

# Use a .txt file as target list
python replacetag.py targets.txt --tags "old=new"

# Recursively process subdirectories
python replacetag.py path/to/images --tags "old=new" -r

# Exclude files matching glob patterns
python replacetag.py path --tags "old=new" --exclude "*thumb*"

# Via PATH
replacetag
replacetag image.jpg --tags "1girl=solo"
replacetag folder --tags_file repls.txt
```

To remove a tag without a replacement, use `--tags "unwanted_tag="` (equals sign with empty new name). If neither `--tags` nor `--tags_file` is given, you'll be prompted interactively.

| Flag | Short | Description |
|------|-------|-------------|
| `--tags` | | Comma-separated `old=new` replacements |
| `--tags_file` | | Read replacements from a .txt file (one per line) |
| `--recursive` | `-r` | Process subdirectories |
| `--exclude` | | Glob patterns to exclude (comma-separated) |

### Saving Tags (Backup)

Exports tags from images to a JSON backup file. Useful for recovery or batch editing tags externally.

```bash
# Save all tags from current directory
python savetags.py

# Save tags from a specific folder or files
python savetags.py path/to/images
python savetags.py img1.jpg img2.png

# Save to a specific path
python savetags.py -o mybackup.json

# Auto-sequence (next available number)
python savetags.py -s
python savetags.py -o mybackup.json -s

# Overwrite existing
python savetags.py -ow
python savetags.py -o mybackup.json -ow

# Append to existing (merge, no duplicates)
python savetags.py -a
python savetags.py -o mybackup.json -a

# Rename the new file
python savetags.py -rn

# Rename the existing file
python savetags.py -ro

# Exclude files matching glob patterns
python savetags.py path/to/images --exclude "*thumb*,*small*"

# Recursively scan subdirectories
python savetags.py folder -r

# Via PATH
savetags
savetags -o mybackup.json -s
```

If no mode flag is given and the target file exists, you'll be prompted:
```
tags_backup.json already exists.
[N] Auto-sequence  [RN] Rename new  [RO] Rename old  [OW] Overwrite  [A] Append
Choose:
```

| Flag | Short | Description |
|------|-------|-------------|
| `--output` | `-o` | Output path (any mode) |
| `--overwrite` | `-ow` | Replace existing file |
| `--append` | `-a` | Merge into existing file |
| `--sequencenew` | `-s` | Pick next available number |
| `--renamenew` | `-rn` | Choose a new name for the output |
| `--renameold` | `-ro` | Rename existing file, then write new

### Restoring Tags

Reads a JSON backup and writes tags back to matching images. Matches files by relative path first, then falls back to filename.

```bash
# Restore tags from default tags_backup.json to all images in current directory
python restoretags.py

# Restore from a specific backup file
python restoretags.py --backup mybackup.json

# Restore to a specific folder or files
python restoretags.py path/to/images
python restoretags.py img1.jpg img2.png

# Append backup tags to existing tags (never duplicates)
python restoretags.py path/to/images --append

# Exclude files matching glob patterns
python restoretags.py --backup backup.json --exclude "*thumb*"

# Recursively scan subdirectories
python restoretags.py folder -r

# Via PATH
restoretags
restoretags --backup mybackup.json
```

By default, tags are **overwritten** on the image. Use `--append` / `-a` to merge with any existing tags.

### Scrubbing Suspicious Tags

Detects and removes non-tag data (coordinates, serialized floats, Lightroom parameters) that may have been mistakenly written into the keyword field by buggy metadata parsers.

```bash
# Dry-run: scan and show suspicious tags without modifying anything
python scrubtags.py
python scrubtags.py path/to/images
python scrubtags.py image.jpg

# Actually remove the suspicious tags
python scrubtags.py image.jpg --clean
python scrubtags.py path/to/images --clean

# Recursively scan subdirectories
python scrubtags.py folder --clean -r

# Exclude files matching glob patterns
python scrubtags.py path --clean --exclude "*thumb*,*backup*"

# Via PATH
scrubtags
scrubtags image.jpg --clean
```

Running without `--clean` is a safe dry-run — it prints which tags it would remove, along with a full list of all unique suspicious patterns found. Pass `--clean` to actually remove them.
