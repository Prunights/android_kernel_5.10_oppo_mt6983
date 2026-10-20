import os

dec = {}
for line in open('decisions.tsv'):
    p = line.rstrip('\n').split('\t')
    if len(p) >= 3 and p[0] != 'path':
        dec[(p[0], int(p[1]))] = p[2]

files = sorted(set(k[0] for k in dec))
resolved = 0
failed = []

for path in files:
    if not os.path.isfile(path):
        continue
    data = open(path, encoding='utf-8', errors='surrogateescape').read()
    lines = data.split('\n')
    out = []
    i = 0
    idx = 0
    ok = True
    while i < len(lines):
        if lines[i].startswith('<<<<<<< '):
            o = []
            b = []
            t = []
            i += 1
            while i < len(lines) and not lines[i].startswith('||||||| '):
                o.append(lines[i]); i += 1
            i += 1
            while i < len(lines) and not lines[i].startswith('======='):
                b.append(lines[i]); i += 1
            i += 1
            while i < len(lines) and not lines[i].startswith('>>>>>>> '):
                t.append(lines[i]); i += 1
            i += 1
            d = dec.get((path, idx))
            if d == 'O':
                out.extend(o)
            elif d == 'T':
                out.extend(t)
            elif d == 'OT':
                out.extend(o); out.extend(t)
            elif d == 'TO':
                out.extend(t); out.extend(o)
            else:
                out.append('<<<<<<< ours'); out.extend(o)
                out.append('||||||| base'); out.extend(b)
                out.append('======='); out.extend(t)
                out.append('>>>>>>> theirs')
                ok = False
            idx += 1
        else:
            out.append(lines[i]); i += 1
    if ok:
        open(path, 'w', encoding='utf-8', errors='surrogateescape').write('\n'.join(out))
        resolved += 1
        print('resolved:', path, 'blocks:', idx)
    else:
        failed.append(path)
        print('PENDING:', path, 'blocks:', idx)

print('== summary ==')
print('resolved files: %d, pending files: %d' % (resolved, len(failed)))
for f in failed:
    print('  pending:', f)

# ---- 兜底：整文件策略 ----
import subprocess
THEIRS_PREFIX = ('fs/nfsd/', 'fs/lockd/', 'fs/notify/', 'net/sunrpc/', 'net/bluetooth/',
                 'net/core/net_namespace.c', 'net/xfrm/', 'net/netfilter/', 'arch/x86/', 'Documentation/')
OURS_FILES = ('drivers/usb/typec/tcpm/tcpm.c', 'drivers/dma/mediatek/mtk-uart-apdma.c',
              'drivers/scsi/ufs/ufshcd.c')
THEIRS_FILES = ('include/linux/compiler-clang.h',)

def unmerged():
    out = subprocess.run(['git', 'ls-files', '-u'], capture_output=True, text=True).stdout
    return sorted(set(l.split('\t')[1] for l in out.splitlines() if '\t' in l))

def take(path, stage):
    r = subprocess.run(['git', 'show', ':%d:%s' % (stage, path)], capture_output=True)
    if r.returncode != 0:
        print('STAGE-FAIL', stage, path, r.stderr.decode()[:120])
        return False
    open(path, 'wb').write(r.stdout)
    subprocess.run(['git', 'add', '--', path])
    return True

auto = 0
for p in unmerged():
    if p in OURS_FILES:
        if take(p, 2):
            auto += 1
            print('WHOLE-OURS:', p)
    elif p in THEIRS_FILES or p.startswith(THEIRS_PREFIX):
        if take(p, 3):
            auto += 1
            print('WHOLE-THEIRS:', p)
    else:
        print('UNHANDLED:', p)

print('whole-file resolved:', auto)
print('final unmerged:', len(unmerged()))
