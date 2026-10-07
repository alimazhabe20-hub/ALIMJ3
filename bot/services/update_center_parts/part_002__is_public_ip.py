# Auto-split part 2: _is_public_ip
def _is_public_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified)
    except ValueError:
        return True
