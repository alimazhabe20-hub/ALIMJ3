# Auto-split part 14: _detect_chart_patterns
def _detect_chart_patterns(highs, lows, closes, atr=None):
    """تشخیص محافظه‌کارانه الگوهای کلاسیک قیمت و وضعیت «در حال تشکیل».
    فقط وقتی هندسه الگو به اندازه کافی واضح باشد خروجی می‌دهد؛ در غیر این صورت [] است.
    """
    n=len(closes)
    if n < 45:
        return []
    atr=float(atr or 0)
    scale=max(atr, abs(closes[-1])*0.002)

    def swings(arr, mode):
        pts=[]
        for i in range(3, len(arr)-3):
            w=arr[i-3:i+4]
            if mode=='h' and arr[i] >= max(w): pts.append((i,float(arr[i])))
            if mode=='l' and arr[i] <= min(w): pts.append((i,float(arr[i])))
        return pts

    sh=swings(highs,'h')[-8:]
    sl=swings(lows,'l')[-8:]
    out=[]
    tol=max(scale*1.8, abs(closes[-1])*0.006)

    # Double top / bottom: two comparable extrema separated by a meaningful valley/peak.
    if len(sh)>=2:
        a,b=sh[-2],sh[-1]
        between=lows[a[0]:b[0]+1]
        if b[0]-a[0]>=5 and between:
            valley=min(between)
            if abs(a[1]-b[1])<=tol and min(a[1],b[1])-valley>=scale*1.2:
                neckline=valley
                state='تکمیل‌شده' if closes[-1] < neckline else 'در حال تشکیل'
                target=neckline-(max(a[1],b[1])-neckline)
                out.append({'name':'دو قله (Double Top)','state':state,'trigger':neckline,'target':target,'bias':'نزولی'})
    if len(sl)>=2:
        a,b=sl[-2],sl[-1]
        between=highs[a[0]:b[0]+1]
        if b[0]-a[0]>=5 and between:
            peak=max(between)
            if abs(a[1]-b[1])<=tol and peak-max(a[1],b[1])>=scale*1.2:
                neckline=peak
                state='تکمیل‌شده' if closes[-1] > neckline else 'در حال تشکیل'
                target=neckline+(neckline-min(a[1],b[1]))
                out.append({'name':'دو کف (Double Bottom)','state':state,'trigger':neckline,'target':target,'bias':'صعودی'})

    # Head & shoulders / inverse H&S.
    if len(sh)>=3:
        l,h,r=sh[-3],sh[-2],sh[-1]
        lows_between=lows[l[0]:r[0]+1]
        if h[1]>l[1]+scale and h[1]>r[1]+scale and abs(l[1]-r[1])<=tol and lows_between:
            nl=(lows[l[0]:h[0]+1] and min(lows[l[0]:h[0]+1]), lows[h[0]:r[0]+1] and min(lows[h[0]:r[0]+1]))
            neckline=sum(x for x in nl if x is not None)/len([x for x in nl if x is not None])
            state='تکمیل‌شده' if closes[-1] < neckline else 'در حال تشکیل'
            target=neckline-(h[1]-neckline)
            out.append({'name':'سر و شانه (Head & Shoulders)','state':state,'trigger':neckline,'target':target,'bias':'نزولی'})
    if len(sl)>=3:
        l,h,r=sl[-3],sl[-2],sl[-1]
        highs_between=highs[l[0]:r[0]+1]
        if h[1]<l[1]-scale and h[1]<r[1]-scale and abs(l[1]-r[1])<=tol and highs_between:
            hs=(max(highs[l[0]:h[0]+1]), max(highs[h[0]:r[0]+1]))
            neckline=sum(hs)/2
            state='تکمیل‌شده' if closes[-1] > neckline else 'در حال تشکیل'
            target=neckline+(neckline-h[1])
            out.append({'name':'سر و شانه معکوس (Inverse H&S)','state':state,'trigger':neckline,'target':target,'bias':'صعودی'})

    # Triple top / bottom from three comparable swings.
    if len(sh)>=3:
        a,b,c=sh[-3:]
        if min(b[0]-a[0],c[0]-b[0])>=4 and max(a[1],b[1],c[1])-min(a[1],b[1],c[1])<=tol:
            nl=min(lows[a[0]:c[0]+1])
            state='تکمیل‌شده' if closes[-1] < nl else 'در حال تشکیل'
            out.append({'name':'سه قله (Triple Top)','state':state,'trigger':nl,'target':nl-(a[1]-nl),'bias':'نزولی'})
    if len(sl)>=3:
        a,b,c=sl[-3:]
        if min(b[0]-a[0],c[0]-b[0])>=4 and max(a[1],b[1],c[1])-min(a[1],b[1],c[1])<=tol:
            nl=max(highs[a[0]:c[0]+1])
            state='تکمیل‌شده' if closes[-1] > nl else 'در حال تشکیل'
            out.append({'name':'سه کف (Triple Bottom)','state':state,'trigger':nl,'target':nl+(nl-a[1]),'bias':'صعودی'})

    # Triangles / wedges / flags are detected from compression of recent range.
    recent=closes[-30:]
    if len(recent)>=20:
        first=max(recent[:10])-min(recent[:10]); last=max(recent[-10:])-min(recent[-10:])
        if first>0 and last/first < 0.72:
            if sh and sl:
                hi_slope=sh[-1][1]-sh[-3][1] if len(sh)>=3 else 0
                lo_slope=sl[-1][1]-sl[-3][1] if len(sl)>=3 else 0
                if hi_slope<0 and lo_slope>0:
                    out.append({'name':'مثلث متقارن (Symmetrical Triangle)','state':'در حال تشکیل','trigger':None,'target':None,'bias':'خنثی تا شکست'})
                elif hi_slope<0 and lo_slope<0:
                    out.append({'name':'مثلث نزولی (Descending Triangle)','state':'در حال تشکیل','trigger':min(lows[-10:]),'target':None,'bias':'نزولی در صورت شکست'})
                elif hi_slope>0 and lo_slope>0:
                    out.append({'name':'مثلث صعودی (Ascending Triangle)','state':'در حال تشکیل','trigger':max(highs[-10:]),'target':None,'bias':'صعودی در صورت شکست'})

    # Rectangle / range: repeated touches near both boundaries without directional breakout.
    if len(recent) >= 24:
        rh=max(highs[-24:]); rl=min(lows[-24:]); mid=(rh+rl)/2
        upper=sum(1 for x in highs[-24:] if abs(x-rh)<=tol)
        lower=sum(1 for x in lows[-24:] if abs(x-rl)<=tol)
        if upper>=2 and lower>=2 and (rh-rl) > scale*3 and not (closes[-1]>rh or closes[-1]<rl):
            out.append({'name':'مستطیل / رنج (Rectangle)','state':'در حال تشکیل','trigger':rh,'target':None,'bias':'خنثی تا شکست'})

    # Pennant/flag proxy: sharp prior impulse followed by tight consolidation.
    if len(closes) >= 30:
        impulse=abs(closes[-21]-closes[-30])
        cons=max(closes[-12:])-min(closes[-12:])
        if impulse > scale*5 and cons < impulse*0.45:
            direction='صعودی' if closes[-21] > closes[-30] else 'نزولی'
            out.append({'name':('پرچم/پرچم سه‌گوش صعودی (Bull Flag/Pennant)' if direction=='صعودی' else 'پرچم/پرچم سه‌گوش نزولی (Bear Flag/Pennant)'), 'state':'در حال تشکیل','trigger':max(highs[-12:]) if direction=='صعودی' else min(lows[-12:]), 'target':None, 'bias':direction+' در صورت شکست'})

    # Cup & handle proxy: rounded recovery followed by a shallow pullback.
    if len(closes) >= 50:
        w=closes[-50:]; left=max(w[:15]); bottom=min(w[15:35]); right=max(w[35:45]); handle_low=min(w[-10:])
        if left>bottom and right >= left*0.96 and handle_low < right and handle_low > bottom*1.03:
            trigger=max(w[-10:])
            out.append({'name':'فنجان و دسته (Cup & Handle)','state':'در حال تشکیل','trigger':trigger,'target':trigger+(trigger-bottom),'bias':'صعودی در صورت شکست'})

    # Rising/falling wedge from opposing narrowing slopes.
    if len(sh)>=3 and len(sl)>=3:
        hs=sh[-3:]; ls=sl[-3:]
        hdelta=hs[-1][1]-hs[0][1]; ldelta=ls[-1][1]-ls[0][1]
        if hdelta>0 and ldelta>0 and hdelta < ldelta*0.9:
            out.append({'name':'کنج صعودی (Rising Wedge)','state':'در حال تشکیل','trigger':None,'target':None,'bias':'نزولی محتمل پس از شکست'})
        elif hdelta<0 and ldelta<0 and abs(hdelta) < abs(ldelta)*0.9:
            out.append({'name':'کنج نزولی (Falling Wedge)','state':'در حال تشکیل','trigger':None,'target':None,'bias':'صعودی محتمل پس از شکست'})

    # Deduplicate by name, prefer completed over forming.
    final=[]
    for x in out:
        old=next((z for z in final if z['name']==x['name']),None)
        if old is None or (x['state']=='تکمیل‌شده' and old['state']!='تکمیل‌شده'):
            if old: final.remove(old)
            final.append(x)
    return final[:4]
