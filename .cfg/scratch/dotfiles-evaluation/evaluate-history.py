#!/usr/bin/env python3
"""Two fake machines and a local Git remote; no live configs or services."""
from pathlib import Path
import subprocess,json,tempfile
root=Path(tempfile.mkdtemp(prefix='cfg-mise-history-'))
exe='/tmp/cfg-dotfiles-evaluation-2026-11-06/bin/mise'
records=[]
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def run(h,args,expect=0):
 h.mkdir(parents=True,exist_ok=True)
 e={'HOME':str(h),'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','SHELL':'/bin/sh','LANG':'en_US.UTF-8','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','MISE_YES':'1','MISE_AUTO_INSTALL':'0','MISE_DISABLE_UPDATE_CHECK':'1','MISE_TRUSTED_CONFIG_PATHS':str(root),'MISE_HISTORY_NOTIFY':'false'}
 for k,t in [('XDG_CONFIG_HOME','.config'),('XDG_DATA_HOME','.local/share'),('XDG_CACHE_HOME','.cache'),('XDG_STATE_HOME','.local/state')]:e[k]=str(h/t)
 p=subprocess.run(args,env=e,cwd=h,text=True,capture_output=True)
 records.append({'machine':h.name,'args':args,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 (root/'commands.json').write_text(json.dumps(records,indent=2))
 print(h.name,' '.join(args[1:]),'code',p.returncode,flush=True)
 if expect is not None and p.returncode!=expect:raise RuntimeError(records[-1])
 return p
A=root/'a';B=root/'b';origin=root/'remote.git'
run(root,['git','init','--bare','--initial-branch=main',str(origin)])
for h in [A,B]:
 write(h/'.config/mise/config.toml','[settings.history]\nnotify = false\nsync = "manual"\n')
write(A/'.config/demo/settings.json','{\n  "plugin": "base",\n  "theme": "light"\n}\n')
write(A/'.config/demo/other.txt','base\n')
run(A,[exe,'dot','track',str(A/'.config/demo/settings.json'),str(A/'.config/demo/other.txt')])
run(A,[exe,'dot','origin','set',str(origin),'--sync','manual','--yes'])
run(B,[exe,'bootstrap','--adopt',str(origin),'--yes'])
print('ROOT',root)
checks=[]
def check(name,ok):
 checks.append({'check':name,'passed':bool(ok)})
 if not ok:raise AssertionError(name)
def m(h,*args,expect=0):return run(h,[exe,'dot',*args],expect=expect)
def settings(h):return h/'.config/demo/settings.json'
def other(h):return h/'.config/demo/other.txt'
try:
 check('second machine adopts tracked file',settings(B).read_text()==settings(A).read_text())
 write(settings(A),'{\n  "plugin": "alpha",\n  "theme": "light"\n}\n')
 m(A,'watch','--once')
 check('one-shot watcher captures app edit','unsaved changes:' not in m(A,'status').stdout)
 m(A,'sync');m(B,'sync')
 check('sync leaves live file unchanged','base' in settings(B).read_text())
 m(B,'pull')
 check('pull propagates one-sided app change',json.loads(settings(B).read_text())['plugin']=='alpha')
 # Different lines and JSON keys in the same file: both machines diverge.
 write(settings(A),'{\n  "plugin": "alpha",\n  "theme": "dark"\n}\n')
 write(settings(B),'{\n  "plugin": "beta",\n  "theme": "light"\n}\n')
 m(A,'save');m(B,'save');m(A,'sync')
 p=m(B,'sync',expect=None)
 check('same file different JSON keys conflicts','conflict(s)' in p.stdout+p.stderr)
 diff=m(B,'conflicts',str(settings(B)))
 check('conflict comparison exposes both values','dark' in diff.stdout and 'beta' in diff.stdout)
 p=m(B,'pull',expect=None)
 check('unresolved pull leaves live JSON intact',p.returncode!=0 and json.loads(settings(B).read_text())=={'plugin':'beta','theme':'light'})
 write(settings(B),'{\n  "plugin": "beta",\n  "theme": "dark"\n}\n')
 m(B,'save');m(B,'pull','--keep-local',str(settings(B)));m(B,'sync')
 m(A,'sync');m(A,'pull')
 check('manual combined result converges',json.loads(settings(A).read_text())==json.loads(settings(B).read_text())=={'plugin':'beta','theme':'dark'})
 # Independent files diverge and reconcile without manual file conflicts.
 write(settings(A),'{\n  "plugin": "beta",\n  "theme": "sepia"\n}\n')
 write(other(B),'independent B edit\n')
 m(A,'save');m(B,'save');m(A,'sync');m(B,'sync');m(B,'pull');m(B,'sync');m(A,'sync');m(A,'pull')
 check('different-file edits converge without conflict',settings(A).read_text()==settings(B).read_text() and other(A).read_text()==other(B).read_text()=='independent B edit\n')
 # A template is not reconstructed from an app's changes to its target.
 conf=A/'.config/mise/config.toml'
 write(A/'templates/demo.tera','value={{ vars.example }}\n')
 with conf.open('a') as f:
  f.write('\n[vars]\nexample = "source"\n[dotfiles."~/.config/demo/rendered.toml"]\nsource = "'+str(A/'templates/demo.tera')+'"\nmode = "template"\n')
 m(A,'apply');m(A,'track',str(A/'.config/demo/rendered.toml'))
 write(A/'.config/demo/rendered.toml','value=app\n');m(A,'watch','--once')
 check('watching generated target leaves template unchanged',(A/'templates/demo.tera').read_text()=='value={{ vars.example }}\n')
 m(A,'apply')
 check('apply restores template despite captured target drift',(A/'.config/demo/rendered.toml').read_text()=='value=source\n')
finally:
 out=Path.home()/'.cfg/scratch/dotfiles-evaluation/history-results.json'
 out.write_text(json.dumps({'version':'2026.11.3','sandbox':str(root),'checks':checks,'commands':records},indent=2)+'\n')
print(str(len(checks))+' checks passed')
