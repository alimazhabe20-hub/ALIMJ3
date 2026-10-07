"""v77_platform: performance responsibilities."""
from .v77_platform_common import *  # noqa: F401,F403
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def cache_get(key: str) -> Any:
    k=str(key); x=_CACHE.get(k)
    if not x:return None
    if x[0]<=time.monotonic():_CACHE.pop(k,None);return None
    _CACHE.move_to_end(k);return x[1]

def cache_set(key: str, value: Any, ttl: float=30) -> None:
    k=str(key);_CACHE[k]=(time.monotonic()+max(.5,float(ttl)),value);_CACHE.move_to_end(k)
    while len(_CACHE)>CACHE_MAX:_CACHE.popitem(last=False)

def performance_snapshot() -> dict[str,Any]:
    try:
        c=_db(); rows=c.execute("SELECT latency_ms,ok FROM v77_perf ORDER BY id DESC LIMIT 1000").fetchall();c.close()
        lat=[float(r[0]) for r in rows];err=sum(not bool(r[1]) for r in rows)
    except Exception:lat=[];err=0
    return {"samples":len(lat),"avg_ms":round(sum(lat)/len(lat),2) if lat else 0,"p95_ms":round(sorted(lat)[max(0,int(len(lat)*.95)-1)],2) if lat else 0,"error_rate":round(err/len(lat),4) if lat else 0,"cache_items":len(_CACHE)}

def record_performance(component: str, latency_ms: float, ok: bool=True) -> None:
    try:
        c=_db();c.execute("INSERT INTO v77_perf(component,latency_ms,ok) VALUES(?,?,?)",(redact(component,160),float(latency_ms),int(ok)));c.commit();c.close()
    except Exception:pass

def release_gate(root: str|Path=".") -> dict[str,Any]:
    root=Path(root); syntax=[]; forbidden=[]; count=0
    for p in root.rglob("*.py"):
        count+=1
        try:ast.parse(p.read_text(encoding="utf-8"))
        except Exception:syntax.append(str(p))
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".db",".sqlite",".sqlite3",".pyc",".pyo"} and "__pycache__" not in p.parts and p.parts and p.parts[0] not in {"data","runtime","backups"}:forbidden.append(str(p))
    required=["requirements.txt","Dockerfile","render.yaml","bot/main.py"]
    missing=[x for x in required if not (root/x).exists()]
    return {"ok":not syntax and not forbidden and not missing,"python_files":count,"syntax_failures":syntax[:50],"forbidden_artifacts":forbidden[:50],"missing_required":missing}

def run_regression_tests(root: str|Path=".") -> dict[str,Any]:
    import subprocess, sys
    root=str(root)
    try:
        proc=subprocess.run([sys.executable,"-m","pytest","-q","tests"],cwd=root,text=True,capture_output=True,timeout=180)
        return {"ok":proc.returncode==0,"returncode":proc.returncode,"summary":redact((proc.stdout or "").splitlines()[-5:],3000)}
    except Exception:
        return {"ok":False,"returncode":-1,"summary":"pytest execution unavailable"}
