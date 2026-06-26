import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from PIL.PngImagePlugin import PngInfo


XMP_HEADER = b'http://ns.adobe.com/xap/1.0/\x00'
EXIF_HEADER = b'Exif\x00\x00'
EXIF_TAG_TAGS = {0x9c9d, 0x9c9e, 0x9c9f, 0x9ca0, 0x9ca2, 0x9ca4}


def _register_ns():
    ET.register_namespace('x', 'adobe:ns:meta/')
    ET.register_namespace('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')


def build_xmp(tags: set[str]) -> bytes:
    _register_ns()
    rdf = ET.Element('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF')
    desc = ET.SubElement(rdf, '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description')
    desc.set('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', '')
    subj = ET.SubElement(desc, '{http://purl.org/dc/elements/1.1/}subject')
    bag = ET.SubElement(subj, '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
    for tag in sorted(tags):
        li = ET.SubElement(bag, '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        li.text = tag
    xmpmeta = ET.Element('{adobe:ns:meta/}xmpmeta')
    xmpmeta.append(rdf)
    body = ET.tostring(xmpmeta, encoding='unicode')
    packet = '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>\n' + body + '\n<?xpacket end="w"?>'
    return packet.encode('utf-8')


def _parse_xmp_xml(xml_data: str) -> set[str]:
    root = ET.fromstring(xml_data)
    ns = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dc': 'http://purl.org/dc/elements/1.1/',
    }
    return {li.text.strip() for li in root.findall('.//dc:subject//rdf:li', ns) if li.text}


# ─── JPEG ──────────────────────────────────────────────────────────────


def _read_jpeg_tags(data: bytes) -> set[str]:
    tags = set()
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xDA, 0xD9):
            break
        seg_len = struct.unpack('>H', data[i+2:i+4])[0]
        seg_end = i + 2 + seg_len
        if seg_end > len(data):
            break
        if marker == 0xE1:
            payload = data[i+4:i+2+seg_len]
            if payload[:28] == b'http://ns.adobe.com/xap/1.0/':
                try:
                    tags.update(_parse_xmp_xml(payload[29:]))
                except ET.ParseError:
                    pass
            elif payload[:6] == EXIF_HEADER:
                tiff = payload[6:]
                bo = '>' if tiff[:2] == b'MM' else '<'
                ifdoffset = struct.unpack(bo + 'I', tiff[4:8])[0]
                base = i + 4 + 6
                num = struct.unpack(bo + 'H', data[base+ifdoffset:base+ifdoffset+2])[0]
                entry_base = base + ifdoffset + 2
                for idx in range(num):
                    entry = data[entry_base + idx*12 : entry_base + idx*12 + 12]
                    tag = struct.unpack(bo + 'H', entry[0:2])[0]
                    typ = struct.unpack(bo + 'H', entry[2:4])[0]
                    cnt = struct.unpack(bo + 'I', entry[4:8])[0]
                    val_off = struct.unpack(bo + 'I', entry[8:12])[0]
                    if tag in EXIF_TAG_TAGS and typ in (1, 7) and cnt > 0:
                        raw = data[base+val_off:base+val_off+cnt] if cnt > 4 else entry[8:8+cnt]
                        try:
                            text = raw.decode('utf-16-le').rstrip('\x00').strip()
                            if text:
                                for t in text.split(';'):
                                    t = t.strip()
                                    if t:
                                        tags.add(t)
                        except UnicodeDecodeError:
                            pass
        elif marker == 0xED:
            payload = data[i+4:i+2+seg_len]
            if payload[:4] == b'8BIM':
                pos = 4
                while pos < len(payload):
                    res_id = struct.unpack('>H', payload[pos:pos+2])[0]
                    pos += 2
                    if payload[pos:pos+1] == b'\x00':
                        pos += 1
                    else:
                        name_len = struct.unpack('>B', payload[pos:pos+1])[0]
                        pos += 1 + name_len
                        if pos % 2:
                            pos += 1
                    data_len = struct.unpack('>I', payload[pos:pos+4])[0]
                    pos += 4
                    if res_id == 0x0404:
                        kw_data = payload[pos:pos+data_len]
                        k = 0
                        while k < len(kw_data) - 1:
                            kw_len = struct.unpack('>B', kw_data[k:k+1])[0]
                            if kw_len and k + 1 + kw_len <= len(kw_data):
                                kw = kw_data[k+1:k+1+kw_len].decode('ascii', errors='replace')
                                tags.add(kw.strip())
                            k += 1 + kw_len
                    pos += data_len
                    if pos % 2:
                        pos += 1
        i += 2 + seg_len
    return tags


def _write_jpeg_tags(path: Path, tags: set[str]):
    data = bytearray(path.read_bytes())
    if data[:2] != b'\xff\xd8':
        return False
    xmp_data = build_xmp(tags)
    xmp_marker = struct.pack('>H', len(XMP_HEADER) + len(xmp_data) + 2)
    out = bytearray()
    out.extend(data[:2])
    i = 2
    wrote = False
    while i < len(data):
        if data[i] != 0xFF:
            out.append(data[i])
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xDA:
            if not wrote:
                out.extend(b'\xff\xe1')
                out.extend(xmp_marker)
                out.extend(XMP_HEADER)
                out.extend(xmp_data)
                wrote = True
            out.extend(data[i:])
            break
        if marker == 0xD9:
            out.extend(data[i:])
            break
        seg_len = struct.unpack('>H', data[i+2:i+4])[0]
        is_xmp = marker == 0xE1 and data[i+4:i+4+28] == XMP_HEADER[:-1]
        if not is_xmp:
            out.extend(data[i:i+2+seg_len])
        i += 2 + seg_len
    path.write_bytes(bytes(out))
    return True


def _clear_exif_tags(data, seg_start, seg_len):
    tiff_start = seg_start + 4 + 6
    tiff = data[tiff_start:seg_start+2+seg_len]
    bo = '>' if tiff[:2] == b'MM' else '<'
    ifdoffset = struct.unpack(bo + 'I', tiff[4:8])[0]
    num = struct.unpack(bo + 'H', data[tiff_start+ifdoffset:tiff_start+ifdoffset+2])[0]
    entry_base = tiff_start + ifdoffset + 2
    for idx in range(num):
        entry_off = entry_base + idx * 12
        entry = data[entry_off:entry_off + 12]
        tag = struct.unpack(bo + 'H', entry[0:2])[0]
        typ = struct.unpack(bo + 'H', entry[2:4])[0]
        cnt = struct.unpack(bo + 'I', entry[4:8])[0]
        if tag in EXIF_TAG_TAGS and typ in (1, 7) and cnt > 0:
            val_off = struct.unpack(bo + 'I', entry[8:12])[0]
            data[entry_off:entry_off + 12] = b'\x00' * 12
            if cnt > 4:
                data_off = tiff_start + val_off
                data[data_off:data_off + cnt] = b'\x00' * cnt


def _replace_xmp_in_jpeg(path: Path, xmp_data: bytes | None):
    data = bytearray(path.read_bytes())
    if data[:2] != b'\xff\xd8':
        return False, 0
    xmp_magic = b'http://ns.adobe.com/xap/1.0/'
    out = bytearray(data[:2])
    i = 2
    wrote = False
    while i < len(data):
        if data[i] != 0xFF:
            out.append(data[i])
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xDA:
            if xmp_data is not None and not wrote:
                seg = struct.pack('>H', 31 + len(xmp_data))
                out.extend(b'\xff\xe1')
                out.extend(seg)
                out.extend(xmp_magic + b'\x00')
                out.extend(xmp_data)
                wrote = True
            out.extend(data[i:])
            break
        if marker == 0xD9:
            out.extend(data[i:])
            break
        seg_len = struct.unpack('>H', data[i+2:i+4])[0]
        if marker == 0xE1 and data[i+4:i+4+6] == EXIF_HEADER:
            _clear_exif_tags(data, i, seg_len)
            out.extend(data[i:i+2+seg_len])
        elif marker == 0xE1 and data[i+4:i+4+28] == xmp_magic:
            pass
        elif marker == 0xED:
            pass
        else:
            out.extend(data[i:i+2+seg_len])
        i += 2 + seg_len
    old_size = len(data)
    path.write_bytes(bytes(out))
    return True, old_size - len(out)


# ─── PNG ───────────────────────────────────────────────────────────────


def _read_png_tags(path: Path) -> set[str]:
    try:
        img = Image.open(path)
        text = getattr(img, 'text', None) or {}
    except Exception:
        return set()
    xmp_raw = text.get('XML:com.adobe.xmp', '')
    if not xmp_raw:
        return set()
    try:
        return _parse_xmp_xml(xmp_raw)
    except ET.ParseError:
        return set()


def _write_png_tags(path: Path, tags: set[str]):
    try:
        img = Image.open(path)
    except Exception:
        return False
    xmp_data = build_xmp(tags).decode('utf-8')
    info = PngInfo()
    info.add_itxt('XML:com.adobe.xmp', xmp_data, zip='', lang='')
    img.save(path, 'PNG', pnginfo=info)
    return True


# ─── WebP ──────────────────────────────────────────────────────────────


def _read_webp_tags(data: bytes) -> set[str]:
    if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
        return set()
    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos:pos+4]
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        if chunk_size > len(data) - pos - 8:
            break
        if chunk_id == b'XMP ':
            xmp_raw = data[pos+8:pos+8+chunk_size]
            try:
                return _parse_xmp_xml(xmp_raw.decode('utf-8'))
            except (ET.ParseError, UnicodeDecodeError):
                pass
        pos += 8 + chunk_size
        if chunk_size % 2:
            pos += 1
    return set()


def _write_webp_tags(path: Path, tags: set[str]):
    data = bytearray(path.read_bytes())
    if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
        return False
    xmp_data = build_xmp(tags)
    pos = 12
    chunks = []
    found = False
    while pos + 8 <= len(data):
        chunk_id = data[pos:pos+4]
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        if chunk_size > len(data) - pos - 8:
            break
        raw = data[pos+8:pos+8+chunk_size]
        pad = 1 if chunk_size % 2 else 0
        if chunk_id == b'XMP ':
            chunks.append((b'XMP ', bytes(xmp_data)))
            found = True
        else:
            chunks.append((chunk_id, bytes(raw)))
        pos += 8 + chunk_size + pad
    if not found:
        insert = len(chunks)
        for i in range(len(chunks) - 1, -1, -1):
            if chunks[i][0] not in (b'EXIF', b'XMP '):
                insert = i + 1
                break
        chunks.insert(insert, (b'XMP ', bytes(xmp_data)))
    out = bytearray(data[:12])
    for cid, cdata in chunks:
        out.extend(cid)
        out.extend(struct.pack('<I', len(cdata)))
        out.extend(cdata)
        if len(cdata) % 2:
            out.extend(b'\x00')
    out[4:8] = struct.pack('<I', len(out) - 8)
    path.write_bytes(bytes(out))
    return True


# ─── TIFF ──────────────────────────────────────────────────────────────


def _read_tiff_tags(path: Path) -> set[str]:
    try:
        img = Image.open(path)
    except Exception:
        return set()
    try:
        exif = img.getexif()
    except Exception:
        return set()
    tags = set()
    for tag_id in EXIF_TAG_TAGS:
        if tag_id in exif:
            val = exif[tag_id]
            if isinstance(val, bytes):
                try:
                    text = val.decode('utf-16-le').rstrip('\x00').strip()
                    if text:
                        for t in text.split(';'):
                            t = t.strip()
                            if t:
                                tags.add(t)
                except UnicodeDecodeError:
                    pass
            elif isinstance(val, str):
                for t in val.split(';'):
                    t = t.strip()
                    if t:
                        tags.add(t)
    return tags


def _write_tiff_tags(path: Path, tags: set[str]):
    try:
        img = Image.open(path)
    except Exception:
        return False
    xmp_data = build_xmp(tags).decode('utf-8')
    exif_data = img.info.get('exif', b'')
    img.save(path, format='TIFF', exif=exif_data, description=xmp_data if tags else '')
    return True


# ─── Dispatch ──────────────────────────────────────────────────────────


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif'}


def resolve_targets(raw_targets: list[Path]) -> list[Path]:
    """Resolve positional args — normal files/dirs, or .txt files as path lists."""
    resolved = []
    for t in raw_targets:
        if t.suffix.lower() == '.txt':
            try:
                lines = [l.strip().strip('"') for l in t.read_text('utf-8').splitlines() if l.strip()]
                for line in lines:
                    p = Path(line)
                    if p.exists():
                        resolved.append(p)
                    else:
                        print(f'Skipping (not found): {p}')
            except Exception as e:
                print(f'Error reading {t.name}: {e}')
        else:
            resolved.append(t)
    return resolved


def read_tags(path: Path) -> set[str]:
    ext = path.suffix.lower()
    if ext in ('.jpg', '.jpeg'):
        return _read_jpeg_tags(path.read_bytes())
    elif ext == '.png':
        return _read_png_tags(path)
    elif ext == '.webp':
        return _read_webp_tags(path.read_bytes())
    elif ext in ('.tiff', '.tif'):
        return _read_tiff_tags(path)
    return set()


def write_tags(path: Path, tags: set[str]):
    ext = path.suffix.lower()
    if ext in ('.jpg', '.jpeg'):
        return _write_jpeg_tags(path, tags)
    elif ext == '.png':
        return _write_png_tags(path, tags)
    elif ext == '.webp':
        return _write_webp_tags(path, tags)
    return False


def replace_xmp(path: Path, xmp_data: bytes | None):
    """Remove-tags variant: replace XMP, clear EXIF/Photoshop."""
    ext = path.suffix.lower()
    if ext in ('.jpg', '.jpeg'):
        ok, _ = _replace_xmp_in_jpeg(path, xmp_data)
        return ok
    elif ext == '.png':
        if xmp_data is None:
            return _write_png_tags(path, set())
        return False
    elif ext == '.webp':
        if xmp_data is None:
            return _write_webp_tags(path, set())
        return False
    return False
