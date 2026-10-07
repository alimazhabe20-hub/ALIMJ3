from pathlib import Path
import ast
import hashlib
ROOT=Path(__file__).resolve().parents[1]

def test_quality_contract():
 p=(ROOT/"pyproject.toml").read_text(); assert "[tool.ruff]" in p and "[tool.mypy]" in p; assert (ROOT/"scripts/run_quality.py").exists()

def test_typed_modules_are_typed():
 for rel in ("bot/database_core.py","bot/database_migrations.py","bot/features/market/finance_core.py"):
  tree=ast.parse((ROOT/rel).read_text()); missing=[]
  for n in ast.walk(tree):
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.returns is None or any(a.annotation is None for a in n.args.args+n.args.kwonlyargs)):
    missing.append(n.name)
  assert not missing,(rel,missing)

def test_database_core_exception_hygiene():
 tree=ast.parse((ROOT/"bot/database_core.py").read_text())
 assert not any(isinstance(n,ast.ExceptHandler) and (n.type is None or (isinstance(n.type,ast.Name) and n.type.id=="Exception")) for n in ast.walk(tree))

def test_locked_assets():
 assert hashlib.sha256((ROOT/"bot/features/fun/jokes_data.json").read_bytes()).hexdigest()=="dc573e2a954af897350caa4183a98f33d5ed71327fed02c7ebe053d893e3a508"
 req=(ROOT/"requirements.txt").read_text();
