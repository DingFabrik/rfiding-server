def formatted_mac(mac_address):
    if mac_address is None:
        return None
    if ":" not in mac_address:
        return ":".join(
            mac_address[i : i + 2].lower() for i in range(0, len(mac_address), 2)
        )
    return mac_address
