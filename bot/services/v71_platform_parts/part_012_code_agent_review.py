# Auto-split part 12: code_agent_review
def code_agent_review(source:str)->dict:
    """Static-only code agent: syntax, dangerous constructs, imports and complexity hints."""
    result={"ok":True,"syntax":"valid","functions":[],"imports":[],"warnings":[]}
    try:
        tree=ast.parse(source)
        result["functions"]=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))][:100]
        result["imports"]=[a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names][:100]
        dangerous={"eval":"dynamic code execution","exec":"dynamic code execution","__import__":"dynamic import","os.system":"shell execution","subprocess":"process execution"}
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                name=getattr(node.func,"id",None) or getattr(node.func,"attr",None)
                if name in dangerous: result["warnings"].append(dangerous[name])
        result["warnings"]=list(dict.fromkeys(result["warnings"]))[:20]
    except SyntaxError as exc:
        return {"ok":False,"syntax":"invalid","line":exc.lineno,"warnings":[]}
    except Exception:
        return {"ok":False,"syntax":"unavailable","warnings":[]}
    return result
