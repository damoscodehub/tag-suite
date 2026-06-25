# tag-suite

Command-line tools for AI image tagging, tag copying, and tag removal.

`joytag` uses the [JoyTag](https://github.com/fpgaminer/joytag) vision model to automatically tag images with 5000+ tags. `copytag` copies tags between files, and `untag` removes tags.

**Supported formats:** JPEG (`.jpg`, `.jpeg`), PNG (`.png`), WebP (`.webp`), TIFF (`.tiff`, `.tif`).

## Setup

Install dependencies:

```bash
pip install torch torchvision Pillow safetensors transformers einops
```

Download the model from [HuggingFace](https://huggingface.co/fancyfeast/joytag/tree/main) and place it in `models/`. The folder must contain `model.safetensors`, `config.json`, and `top_tags.txt`.

For convenience, add this repo's folder to your `PATH` to run the commands from anywhere.

## Usage

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
