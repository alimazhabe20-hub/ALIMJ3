from typing import Any

# Auto-split part 33: generate_report
def generate_report(title:str,rows:list[dict[str,Any]],fmt:str="json")->tuple[bytes,str,str]:
    safe=re.sub(r"[^\w\- ]+","_",title or "report")[:80] or "report"; fmt=fmt.lower()
    if fmt=="json":return json.dumps({"title":title,"rows":rows},ensure_ascii=False,indent=2).encode(),safe+".json","application/json"
    if fmt=="csv":
        keys=sorted({k for r in rows for k in r});s=io.StringIO();w=csv.DictWriter(s,fieldnames=keys);w.writeheader();w.writerows(rows);return s.getvalue().encode("utf-8-sig"),safe+".csv","text/csv"
    if fmt=="xlsx":
        try:
            from openpyxl import Workbook
            wb=Workbook();ws=wb.active;keys=sorted({k for r in rows for k in r});ws.append(keys)
            for r in rows:ws.append([r.get(k,"") for k in keys])
            b=io.BytesIO();wb.save(b);return b.getvalue(),safe+".xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        except Exception:return generate_report(title,rows,"csv")
    return generate_report(title,rows,"json")
