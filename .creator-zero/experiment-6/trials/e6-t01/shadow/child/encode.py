def encode(d):
    parts = []
    for key, value in d.items():
        k = key.replace(';', '\\;').replace('=', '\\=')
        v = value.replace(';', '\\;').replace('=', '\\=')
        parts.append(k + '=' + v)
    return ';'.join(parts)
