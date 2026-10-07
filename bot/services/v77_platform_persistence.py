"""v77_platform: persistence responsibilities."""
from .v77_platform_common import *  # noqa: F401,F403
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def sqlite_backup(source: str|Path, destination: str|Path) -> dict[str,Any]:
    src=Path(source); dst=Path(destination); dst.parent.mkdir(parents=True,exist_ok=True); tmp=dst.with_suffix(dst.suffix+".tmp")
    try:
        if tmp.exists(): tmp.unlink()
        s=sqlite3.connect(str(src),timeout=10); d=sqlite3.connect(str(tmp),timeout=10)
        with d: s.backup(d)
        s.close(); d.close(); tmp.replace(dst)
        verify=verify_sqlite(dst)
        fp=backup_fingerprint(dst)
        return {"ok":bool(verify["ok"]),"verify":verify,"fingerprint":fp,"path":str(dst)}
    except Exception:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass
        return {"ok":False,"error":"backup_failed"}

def backup_fingerprint(path: str|Path) -> dict[str,Any]:
    p=Path(path)
    if not p.exists() or not p.is_file(): return {"ok":False,"reason":"missing"}
    h=hashlib.sha256(); size=0
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block); size+=len(block)
    return {"ok":True,"sha256":h.hexdigest(),"size":size,"path":str(p)}

def verify_sqlite(path: str|Path) -> dict[str,Any]:
    try:
        c=sqlite3.connect(str(path),timeout=8); integrity=c.execute("PRAGMA integrity_check").fetchone(); quick=c.execute("PRAGMA quick_check").fetchone(); c.close()
        return {"ok":bool(integrity and integrity[0]=="ok" and quick and quick[0]=="ok"),"result":integrity[0] if integrity else "unknown"}
    except Exception: return {"ok":False,"result":"unavailable"}

def backup_manifest(path: str|Path) -> dict[str,Any]:
    fp=backup_fingerprint(path); return {"version":VERSION,"created_at":int(time.time()),"integrity":verify_sqlite(path),"fingerprint":fp}

def restore_plan(current_db: str|Path, candidates: Iterable[str|Path]) -> dict[str,Any]:
    current=Path(current_db); current_size=current.stat().st_size if current.exists() else 0; ranked=[]
    for candidate in candidates:
        p=Path(candidate); v=verify_sqlite(p)
        if v["ok"]: ranked.append({"path":str(p),"size":p.stat().st_size,"score":(1 if p.stat().st_size else 0)+(p.stat().st_size>=current_size)})
    ranked.sort(key=lambda x:(x["score"],x["size"]),reverse=True)
    return {"ok":bool(ranked),"current_size":current_size,"candidates":ranked}

def rotate_backups(directory: str|Path, keep: int=5) -> dict[str,Any]:
    d=Path(directory); files=sorted([p for p in d.glob("*.db") if p.is_file()], key=lambda p:p.stat().st_mtime, reverse=True) if d.exists() else []
    removed=[]
    for p in files[max(1,int(keep)):]:
        try:p.unlink(); removed.append(p.name)
        except OSError: pass
    return {"ok":True,"kept":min(len(files),max(1,int(keep))),"removed":removed}
