#!/usr/bin/env python3
"""Install cfg-owned personal Codex instructions and skills as relative symlinks."""

import argparse
import os
from pathlib import Path
import sys


def install(codex_home):
    source_root = Path(__file__).resolve().parent.parent / 'codex'
    links = [(source_root / 'AGENTS.md', codex_home / 'AGENTS.md')]
    links.extend((source_root / 'skills' / name, codex_home / 'skills' / name)
                 for name in ('wrap-up', 'coding-guidelines', 'disk-cleanup'))
    override = codex_home / 'AGENTS.override.md'
    if override.exists() or override.is_symlink():
        raise RuntimeError('Global override exists; review it before installation: ' + str(override))

    # Check every destination before making any change. Preserve existing user files.
    for source, destination in links:
        if not source.exists():
            raise RuntimeError('Missing cfg source: ' + str(source))
        if destination.is_symlink():
            if destination.resolve() != source.resolve():
                raise RuntimeError('Conflicting symlink; preserved: ' + str(destination))
        elif destination.exists():
            raise RuntimeError('Existing file/directory; preserved: ' + str(destination))

    for source, destination in links:
        if destination.is_symlink():
            print('Already linked: ' + str(destination))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(os.path.relpath(source, destination.parent),
                               target_is_directory=source.is_dir())
        print('Linked: {} -> {}'.format(destination, os.readlink(destination)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-home', type=Path,
                        default=Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex'),
                        help='Codex home; defaults to CODEX_HOME or ~/.codex')
    args = parser.parse_args()
    install(args.codex_home.expanduser().resolve())


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError) as error:
        print('Installation failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
