import os
import sys
from pathlib import Path
from PIL import Image
import torch
import torchvision.transforms.functional as TVF
from Models import VisionModel
from image_metadata import read_tags, write_tags, IMAGE_EXTENSIONS, resolve_targets

CURRENT_DIR = Path(__file__).parent
sys.path.insert(0, str(CURRENT_DIR))
TARGET_DIR = Path.cwd()

MODEL_DIR = CURRENT_DIR / 'models'
THRESHOLD = 0.4

device = 'cuda' if torch.cuda.is_available() else 'cpu'

model = VisionModel.load_model(str(MODEL_DIR), device)
model.eval()

with open(MODEL_DIR / 'top_tags.txt', 'r') as f:
    top_tags = [line.strip() for line in f.readlines() if line.strip()]


def prepare_image(image: Image.Image, target_size: int) -> torch.Tensor:
    image_shape = image.size
    max_dim = max(image_shape)
    pad_left = (max_dim - image_shape[0]) // 2
    pad_top = (max_dim - image_shape[1]) // 2
    padded_image = Image.new('RGB', (max_dim, max_dim), (255, 255, 255))
    padded_image.paste(image, (pad_left, pad_top))
    if max_dim != target_size:
        padded_image = padded_image.resize((target_size, target_size), Image.BICUBIC)
    image_tensor = TVF.pil_to_tensor(padded_image) / 255.0
    image_tensor = TVF.normalize(image_tensor, mean=[0.48145466, 0.4578275, 0.40821073], std=[0.26862954, 0.26130258, 0.27577711])
    return image_tensor


def predict(image: Image.Image) -> set[str]:
    image_tensor = prepare_image(image, model.image_size)
    batch = {'image': image_tensor.unsqueeze(0).to(device)}
    with torch.no_grad():
        if device == 'cuda':
            with torch.amp.autocast_mode.autocast('cuda', enabled=True):
                preds = model(batch)
                tag_preds = preds['tags'].sigmoid().cpu()
        else:
            preds = model(batch)
            tag_preds = preds['tags'].sigmoid().cpu()
    scores = {top_tags[i]: float(tag_preds[0][i]) for i in range(len(top_tags))}
    return {tag for tag, score in scores.items() if score > THRESHOLD}


def collect_images(targets, recursive=False):
    images = []
    for t in targets:
        if not t.exists():
            print(f'Skipping (not found): {t}')
            continue
        if t.is_file():
            if t.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(t)
            else:
                print(f'Skipping (unsupported format): {t}')
        else:
            it = t.rglob('*') if recursive else t.iterdir()
            found = sorted([p for p in it if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS])
            images.extend(found)
    return sorted(set(images))


def main():
    global TARGET_DIR

    raw = sys.argv[1:]
    args = [Path(a) for a in raw if not a.startswith('-')]
    flags = set(a for a in raw if a.startswith('-'))

    overwrite = '--overwrite' in flags
    recursive = '--recursive' in flags or '-r' in flags

    if args:
        targets = resolve_targets(args)
        if not targets:
            print('No valid targets found.')
            return
    else:
        targets = [TARGET_DIR]
    images = collect_images(targets, recursive=recursive)
    if not images:
        print('No supported image files found.')
        return

    for path in images:
        print(f'Processing {path.name} ...', end=' ')

        if overwrite:
            existing = set()
        else:
            existing = read_tags(path)
            if existing:
                print(f'{len(existing)} existing tags', end='')

        image = Image.open(path).convert('RGB')
        predicted = predict(image)
        print(f', {len(predicted)} predicted', end='')

        merged = existing | predicted
        delta = len(merged) - len(existing)
        if delta > 0 and not overwrite:
            print(f', +{delta} new', end='')
        elif overwrite:
            print(f', overwriting', end='')

        write_tags(path, merged)
        print(f' => {len(merged)} total')

    print('\nDone.')


if __name__ == '__main__':
    main()
