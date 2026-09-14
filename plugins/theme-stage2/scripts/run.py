#!/usr/bin/env python3
"""Portable entry point for the theme-stage2 plugin."""
from pathlib import Path
import importlib.util
import importlib.metadata
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))

if len(sys.argv) > 1 and sys.argv[1] == 'doctor':
    deps = {}
    for module, distribution in [('PIL','Pillow'), ('numpy','numpy'), ('scipy','scipy')]:
        available = importlib.util.find_spec(module) is not None
        try:
            version = importlib.metadata.version(distribution) if available else None
        except importlib.metadata.PackageNotFoundError:
            version = None
        deps[module] = {'available': available, 'version': version}
    ready = sys.version_info >= (3,10) and all(d['available'] for d in deps.values())
    print(json.dumps({'python':sys.version.split()[0], 'dependencies':deps,
        'ready_for_local_processing':ready,
        'image_generation':'Provided by the Codex built-in image tool; not invoked or verified by doctor.'}, ensure_ascii=False, indent=2))
    sys.exit(0 if ready else 2)

try:
    import harness
    raise SystemExit(harness.main())
except ImportError as exc:
    print(json.dumps({'error':str(exc), 'hint':'Run doctor with this entry point and use a Python runtime with the packaged requirements installed.'}), file=sys.stderr)
    raise SystemExit(2)
