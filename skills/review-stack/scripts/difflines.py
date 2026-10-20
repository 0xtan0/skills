import re,sys,json
def parse(path):
    files={};cur=None;r=0
    for l in open(path,encoding='utf-8',errors='replace'):
        l=l.rstrip('\n')
        if l.startswith('+++ '):
            cur=l[6:] if l.startswith('+++ b/') else None
            if cur: files.setdefault(cur,{})
            continue
        if l.startswith('--- ') or l.startswith('diff --git'): continue
        m=re.match(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@',l)
        if m: r=int(m.group(1)); continue
        if cur is None: continue
        if l.startswith('+'): files[cur][r]=('+',l[1:]); r+=1
        elif l.startswith(' '): files[cur][r]=(' ',l[1:]); r+=1
        elif l.startswith('-') or l.startswith('\\'): pass
    return files
if __name__=='__main__':
    pr,f,a,b=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
    d=parse(f'{sys.argv[5]}/pr-{pr}.diff').get(f)
    if d is None: print('FILE NOT IN DIFF',f); sys.exit()
    for i in range(a,b+1):
        x=d.get(i); print(f"{i:5}{x[0] if x else 'X'} {x[1] if x else '<not in diff>'}")
