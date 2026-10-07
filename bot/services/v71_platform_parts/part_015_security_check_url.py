# Auto-split part 15: security_check_url
def security_check_url(url:str)->dict:
    from urllib.parse import urlparse
    try:
        p=urlparse(url)
        if p.scheme not in {"http","https"} or not p.hostname: return {"ok":False,"reason":"invalid_scheme"}
        infos=socket.getaddrinfo(p.hostname,None,type=socket.SOCK_STREAM)
        ips=[]
        for info in infos:
            ip=ipaddress.ip_address(info[4][0]); ips.append(str(ip))
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified: return {"ok":False,"reason":"private_or_special_ip","ips":ips}
        return {"ok":True,"ips":ips}
    except Exception: return {"ok":False,"reason":"resolution_failed"}
