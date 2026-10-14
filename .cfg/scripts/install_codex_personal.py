#!/usr/bin/env python3
"""Install cfg-owned personal Codex instructions and approved shared skill links."""

import argparse
import os
from pathlib import Path
import sys


def install(codex_home, skills_home):
    cfg_root = Path(__file__).resolve().parent.parent
    source_root = cfg_root / 'codex'
    shared_root = cfg_root / 'agents' / 'skills'
    names = ('wrap-up', 'coding-guidelines', 'disk-cleanup', 'gh-stack',
             'make-pages-interactive', 'voice-transcription', 'skill-simplifier')
    links = [(source_root / 'AGENTS.md', codex_home / 'AGENTS.md')]
    links.extend((shared_root / name, skills_home / name) for name in names)
    legacy_links = []
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

    for name in names:
        legacy = codex_home / 'skills' / name
        if legacy == skills_home / name:
            continue
        if legacy.is_symlink():
            recognized = ((source_root / 'skills' / name).resolve(),
                          (shared_root / name).resolve())
            if legacy.resolve() not in recognized:
                raise RuntimeError('Unmanaged Codex skill link; preserved: ' + str(legacy))
            legacy_links.append(legacy)
        elif legacy.exists():
            raise RuntimeError('Unmanaged Codex skill directory; preserved: ' + str(legacy))

    for source, destination in links:
        if destination.is_symlink():
            print('Already linked: ' + str(destination))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(os.path.relpath(source, destination.parent),
                               target_is_directory=source.is_dir())
        print('Linked: {} -> {}'.format(destination, os.readlink(destination)))

    for legacy in legacy_links:
        legacy.unlink()
        print('Removed former Codex-only link: ' + str(legacy))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-home', type=Path,
                        default=Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex'),
                        help='Codex home; defaults to CODEX_HOME or ~/.codex')
    parser.add_argument('--skills-home', type=Path, default=Path.home() / '.agents/skills',
                        help='Shared skills directory; defaults to ~/.agents/skills')
    args = parser.parse_args()
    install(args.codex_home.expanduser().resolve(), args.skills_home.expanduser().resolve())


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError) as error:
        print('Installation failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
