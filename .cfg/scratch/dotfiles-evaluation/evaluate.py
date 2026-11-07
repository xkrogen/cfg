#!/usr/bin/env python3
"""Synthetic dotfiles experiments. Requires the four isolated pinned runtimes.

No real dotfiles, credentials, work repositories, package installs, or services are
used. Linux profiles are simulated data on macOS, not native Linux execution.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

ap = argparse.ArgumentParser()
ap.add_argument('--runtime-dir', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
a = ap.parse_args()
root = Path(tempfile.mkdtemp(prefix='cfg-dotfiles-fixtures-'))
commands = []
checks = []


def write(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s)


def env(home):
    home.mkdir(parents=True, exist_ok=True)
    e = {'HOME': str(home), 'PATH': '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
         'SHELL': '/bin/sh', 'LANG': 'en_US.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1',
         'GIT_CONFIG_GLOBAL': '/dev/null', 'NO_COLOR': '1', 'MISE_YES': '1',
         'MISE_AUTO_INSTALL': '0', 'MISE_DISABLE_UPDATE_CHECK': '1'}
    for key, tail in [('XDG_CONFIG_HOME', '.config'), ('XDG_DATA_HOME', '.local/share'),
                      ('XDG_CACHE_HOME', '.cache'), ('XDG_STATE_HOME', '.local/state')]:
        e[key] = str(home / tail)
    e['MISE_TRUSTED_CONFIG_PATHS'] = str(root)
    return e


def run(args, home, cwd=None, expect=0):
    p = subprocess.run([str(x) for x in args], env=env(home), cwd=cwd or root,
                       capture_output=True, text=True)
    commands.append({'argv': [str(x) for x in args], 'code': p.returncode,
                     'stdout': p.stdout, 'stderr': p.stderr})
    if expect is not None and p.returncode != expect:
        raise RuntimeError(commands[-1])
    return p


def check(label, condition, detail=''):
    checks.append({'check': label, 'passed': bool(condition), 'detail': detail})
    if not condition:
        raise AssertionError(label + ': ' + detail)


def repo(p):
    p.mkdir(parents=True, exist_ok=True)
    run(['git', 'init', '-q', '-b', 'master', p], root/'git-home')


def commit(p):
    run(['git', '-C', p, 'add', '.'], root/'git-home')
    run(['git', '-C', p, '-c', 'user.name=Sandbox', '-c',
         'user.email=sandbox@example.invalid', 'commit', '-qm', 'Synthetic fixture'], root/'git-home')


def dotdrop():
    tool = a.runtime_dir/'venv/bin/dotdrop'
    base = root/'dotdrop/base'; work = root/'dotdrop/work'
    repo(base); repo(work)
    write(base/'files/shared', 'persona={{@@ persona @@}} os={{@@ target_os @@}} role={{@@ role @@}}\n')
    write(base/'files/choice', 'base\n')
    write(base/'config.yaml', '''config:
  dotpath: files
  backup: true
  banner: false
variables:
  persona: personal
  target_os: unknown
  role: unknown
dotfiles:
  f_shared:
    src: shared
    dst: ~/.shared
    actions: [marker]
  f_choice:
    src: choice
    dst: ~/.choice
actions:
  marker: 'echo installed >> "$HOME/setup.log"'
profiles:
  _common:
    dotfiles: [f_shared, f_choice]
  mac-laptop:
    include: [_common]
    variables: {target_os: darwin, role: laptop}
  linux-server:
    include: [_common]
    variables: {target_os: linux, role: server}
''')
    write(work/'files/choice', 'work\n')
    write(work/'config.yaml', '''config:
  dotpath: files
  backup: true
  banner: false
  import_configs: [../base/config.yaml]
dotfiles:
  f_choice:
    src: choice
    dst: ~/.choice
profiles:
  work-mac:
    include: [mac-laptop]
    variables: {persona: work}
''')
    commit(base); commit(work)
    for profile, cfg, expected in [('mac-laptop', base, 'persona=personal os=darwin role=laptop'),
                                    ('linux-server', base, 'persona=personal os=linux role=server'),
                                    ('work-mac', work, 'persona=work os=darwin role=laptop')]:
        h = root/'dotdrop'/profile
        cmd = [tool, 'install', '-b', '-f', '-c', cfg/'config.yaml', '-p', profile]
        run(cmd+['--dry'], h)
        check('dotdrop dry run writes no target: '+profile, not (h/'.shared').exists())
        run(cmd, h)
        check('dotdrop imported template/profile: '+profile, (h/'.shared').read_text().strip()==expected,
              (h/'.shared').read_text())
        check('dotdrop same-key override: '+profile, (h/'.choice').read_text().strip()==('work' if cfg==work else 'base'))
        run(cmd, h)
        check('dotdrop unchanged file action skipped: '+profile, (h/'setup.log').read_text().splitlines()==['installed'])
        run(cmd+['--force-actions'], h)
        check('dotdrop explicit force-actions reruns: '+profile, len((h/'setup.log').read_text().splitlines())==2)


def chezmoi():
    tool = a.runtime_dir/'bin/chezmoi'
    base = root/'chezmoi/base'; work = root/'chezmoi/work'
    repo(base); repo(work)
    write(base/'dot_shared.tmpl', 'os={{ .chezmoi.os }} role={{ .role }}\n')
    write(base/'dot_choice', 'base\n')
    write(base/'run_once_10-setup.sh', '#!/bin/sh\necho once >> "$HOME/setup.log"\n')
    write(work/'dot_choice', 'work\n')
    write(work/'dot_work', 'private overlay placeholder\n')
    commit(base); commit(work)
    h = root/'chezmoi/home'
    cfg = root/'chezmoi/config.toml';write(cfg, '[data]\nrole = "laptop"\n')
    def cmd(source, state):
        return [tool, '--source', source, '--destination', h, '--config', cfg,
                '--persistent-state', root/'chezmoi'/state, '--cache', h/'.cache/chezmoi', '--force', 'apply']
    b = cmd(base, 'base-state.boltdb'); w = cmd(work, 'work-state.boltdb')
    run(b+['--dry-run'],h)
    check('chezmoi dry run writes no target', not (h/'.shared').exists())
    run(b,h);run(w,h)
    check('chezmoi two repositories disjoint target', (h/'.work').exists() and (h/'.shared').read_text()=='os=darwin role=laptop\n')
    check('chezmoi last apply wins collision', (h/'.choice').read_text()=='work\n')
    run(b,h)
    check('chezmoi base reapply overwrites overlay collision', (h/'.choice').read_text()=='base\n')
    check('chezmoi run_once skipped on reapply', (h/'setup.log').read_text().splitlines()==['once'])
    write(base/'run_once_10-setup.sh', '#!/bin/sh\necho changed >> "$HOME/setup.log"\n')
    run(b,h)
    check('chezmoi run_once changed content runs again', (h/'setup.log').read_text().splitlines()==['once','changed'])


def stow():
    tool = a.runtime_dir/'stow-install/bin/stow'
    base = root/'stow/base'; work = root/'stow/work';h=root/'stow/home'
    repo(base);repo(work)
    write(base/'common/.shared','base\n');write(work/'work/.work','overlay\n')
    commit(base);commit(work)
    b=[tool,'--no-folding','-d',base,'-t',h,'common']
    w=[tool,'--no-folding','-d',work,'-t',h,'work']
    run(b+['-n'],h);check('stow dry run writes no target',not (h/'.shared').exists())
    run(b,h);run(w,h)
    check('stow separate repo disjoint targets', (h/'.shared').is_symlink() and (h/'.work').is_symlink())
    write(work/'work/.shared','override\n')
    p=run(w,h,expect=None)
    check('stow same target conflict rejected',p.returncode!=0 and (h/'.shared').read_text()=='base\n',p.stderr)


def mise():
    tool=a.runtime_dir/'bin/mise'
    base=root/'mise/base';work=root/'mise/work';h=root/'mise/home';conf=h/'.config/mise'
    repo(base);repo(work)
    write(base/'shared.tmpl','persona={{ vars.persona }} role={{ vars.role }} os={{ os() }}\n')
    write(base/'choice','base\n');write(work/'choice','work\n')
    write(base/'mise.toml','''[vars]
persona = "personal"
role = "laptop"
[dotfiles]
"~/.shared" = { source = "shared.tmpl", mode = "template" }
"~/.choice" = { source = "choice", mode = "copy" }
"~/.combined/base" = { block = "base block", comment = "#" }
[bootstrap.hooks]
post-dotfiles = 'echo base >> "$HOME/setup.log"'
''')
    write(work/'mise.work.toml','''[vars]
persona = "work"
[dotfiles]
"~/.choice" = { source = "choice", mode = "copy" }
"~/.work" = { content = "overlay" }
"~/.combined/work" = { block = "work block", comment = "#" }
[bootstrap.hooks]
post-dotfiles = 'echo work >> "$HOME/setup.log"'
''')
    commit(base);commit(work)
    (conf/'conf.d').mkdir(parents=True)
    (conf/'conf.d/10-base').symlink_to(base,target_is_directory=True)
    (conf/'conf.d/90-work').symlink_to(work,target_is_directory=True)
    write(conf/'config.toml','')
    write(h/'.combined','manual line\n')
    cmd=[tool,'-E','work','dot','apply']
    run(cmd+['--dry-run'],h,cwd=h)
    check('mise dry run writes no target or hook marker',not (h/'.shared').exists() and not (h/'setup.log').exists())
    run(cmd,h,cwd=h)
    check('mise symlinked repo fragments template and variables',(h/'.shared').read_text()=='persona=work role=laptop os=macos\n',(h/'.shared').read_text())
    check('mise same-target winner precomputed',(h/'.choice').read_text()=='work\n')
    check('mise additive marker blocks preserve manual content',all(s in (h/'.combined').read_text() for s in ['manual line','base block','work block']))
    run(cmd,h,cwd=h)
    check('mise hooks run on unchanged second apply',(h/'setup.log').read_text().splitlines()==['base','work','base','work'],(h/'setup.log').read_text())
    # Same entry wins before deployment: repeat run needs no --force.
    check('mise repeated apply retains work winner',(h/'.choice').read_text()=='work\n')
    # Deactivating a profile does not delete its old deployed files.
    run([tool,'dot','apply'],h,cwd=h)
    check('mise deactivated profile restores base winner',(h/'.choice').read_text()=='base\n')
    check('mise deactivated profile leaves old work file',(h/'.work').exists())
    # Fresh server selection exercises role selection separately from work.
    write(base/'mise.server.toml','[vars]\nrole = "server"\n')
    commit(base)
    h2=root/'mise/server-home';conf2=h2/'.config/mise'
    (conf2/'conf.d').mkdir(parents=True)
    (conf2/'conf.d/10-base').symlink_to(base,target_is_directory=True)
    (conf2/'conf.d/90-work').symlink_to(work,target_is_directory=True)
    write(conf2/'config.toml','')
    run([tool,'-E','server','dot','apply'],h2,cwd=h2)
    check('mise server role selected',(h2/'.shared').read_text()=='persona=personal role=server os=macos\n')
    check('mise fresh nonwork profile excludes work target',not (h2/'.work').exists())
    write(conf/'config.toml','include = ["'+str(base/'mise.toml')+'"]\n')
    p=run([tool,'dot','status'],h,cwd=h,expect=None)
    check('mise include rejects dotfiles section',p.returncode!=0 and 'dotfiles' in p.stderr,p.stderr)


try:
    for fn in [dotdrop,chezmoi,stow,mise]:
        fn()
        print(fn.__name__+': completed',flush=True)
finally:
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({'sandbox':str(root),'checks':checks,'commands':commands},indent=2)+'\n')
print(f'{len(checks)} checks passed; fixtures: {root}')
