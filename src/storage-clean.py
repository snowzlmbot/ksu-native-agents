#!/usr/bin/python3
"""Explicit cache cleanup: directory-FD traversal, no symlink or mount following."""
import json, os, stat, time
from pathlib import Path
CACHES=('/root/.cache','/root/.npm/_cacache','/var/cache/apt/archives')

def open_chain(path):
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in Path(path).parts[1:]:
            nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd); fd=nxt
        return fd
    except BaseException: os.close(fd); raise

def clean(fd,dev,deadline,budget):
    total=0; count=0
    with os.scandir(fd) as entries:
        for entry in entries:
            if time.monotonic()>deadline or budget[0]<=0: break
            budget[0]-=1
            st=entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(st.st_mode) or st.st_dev!=dev: continue
            if stat.S_ISDIR(st.st_mode):
                child=os.open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                try: b,n=clean(child,dev,deadline,budget); total+=b; count+=n
                finally: os.close(child)
                try: os.rmdir(entry.name,dir_fd=fd)
                except OSError: pass
            elif stat.S_ISREG(st.st_mode) and time.time()-st.st_mtime>86400:
                # Never follow links, and only reclaim old regenerable cache files.
                os.unlink(entry.name,dir_fd=fd); total+=st.st_size; count+=1
    return total,count

if __name__=='__main__':
    total=count=0; deadline=time.monotonic()+15; budget=[20000]
    for path in CACHES:
        try:
            fd=open_chain(path)
            try: b,n=clean(fd,os.fstat(fd).st_dev,deadline,budget); total+=b; count+=n
            finally: os.close(fd)
        except (FileNotFoundError,NotADirectoryError): pass
    print(json.dumps({'ok':True,'reclaimedBytes':total,'files':count,'note':'只回收超过一天的可再生缓存；未触碰会话/配置/密钥/宿主映射。'},ensure_ascii=False))
