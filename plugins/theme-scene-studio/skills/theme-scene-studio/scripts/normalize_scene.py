"""Fixed scene delivery size; resampling is not native high-resolution generation."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

CONTRACT = {'id': 'scene-4096-h130-v2', 'canvas': [4096, 4096],
            'H_px': 130, 'alpha_threshold': 16}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def normalize_scene(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    record = output.with_suffix('.size.json')
    if output.exists() or record.exists() or source == output:
        raise ValueError('Use a new output path; preserve source and prior records')
    with Image.open(source) as im:
        if im.width != im.height:
            raise ValueError('Scene must be square; regenerate framing, do not stretch or crop')
        original_size = list(im.size)
        result = im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
        if result.size != (4096, 4096):
            result = result.resize((4096, 4096), Image.Resampling.LANCZOS)
        output.parent.mkdir(parents=True, exist_ok=True)
        result.save(output, format='PNG')
    info = {'contract': CONTRACT, 'source': str(source), 'source_sha256': digest(source),
            'source_dimensions': original_size, 'output': str(output),
            'output_sha256': digest(output), 'output_dimensions': [4096, 4096],
            'resampled': original_size != [4096, 4096],
            'native_4096': original_size == [4096, 4096]}
    record.write_text(json.dumps(info, indent=2) + '\n')
    return info

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(normalize_scene(args.source, args.out), indent=2))
