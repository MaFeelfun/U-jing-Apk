# -*- coding: utf-8 -*-
"""axml_app_patch.py - binary AXML patcher:
   1) exact-value string replacements (e.g. StubApplication -> MainApplication)
   2) prefix renames on authorities/permission/meta-data (delegated to axml_auth_patch)
   Rebuilds the string pool (UTF-16LE) so value lengths may change.
"""
import struct
import io

def rebuild_pool_with_replacements(buf, exact_map):
    """rewrite string pool; values in exact_map get replaced."""
    off = 8
    typ, hdrsz, size = struct.unpack_from('<HHI', buf, off)
    assert typ == 0x0001, hex(typ)
    count, styleCount, flags, stringsStart, stylesStart = struct.unpack_from('<IIIII', buf, off + 8)
    is_utf8 = bool(flags & (1 << 8))
    assert not is_utf8, 'expected utf-16 pool'
    chunk_base = off
    base = chunk_base + stringsStart
    offs = struct.unpack_from('<%dI' % count, buf, chunk_base + 28)

    strs = []
    styles_raw = bytes(buf[chunk_base + stylesStart:]) if styleCount else b''
    for i in range(count):
        p = base + offs[i]
        if buf[p:p + 2] == b'\x00\x00':
            strs.append('')
            continue
        ln, = struct.unpack_from('<H', buf, p)
        raw = buf[p + 2:p + 2 + ln * 2]
        texts = raw.decode('utf-16-le')
        v = exact_map.get(texts, texts)
        strs.append(v)

    # re-encode
    enc = bytearray()
    new_offs = []
    for s in strs:
        new_offs.append(len(enc))
        try:
            b16 = s.encode('utf-16-le')
        except UnicodeError:
            b16 = s.encode('utf-16-le', 'replace')
        enc += struct.pack('<H', len(s))
        enc += b16
        enc += b'\x00\x00'
    strings_data = bytes(enc)
    stringsStart_new = hdrsz + count * 4
    pad = (4 - (stringsStart_new % 4)) % 4
    stringsStart_new += pad
    pool_body = b'\x00' * pad + strings_data + styles_raw
    total_body = hdrsz + count * 4 + pad + len(strings_data) + len(styles_raw)
    # align to 4
    while total_body % 4:
        pool_body += b'\x00'
        total_body += 1

    new_hdr = struct.pack('<HHIIIIII', 0x0001, hdrsz, total_body, count, styleCount,
                          flags, stringsStart_new, stylesStart if 0 else stringsStart_new + len(strings_data))
    out = bytearray()
    out += buf[:chunk_base]
    out += new_hdr
    out += struct.pack('<%dI' % count, *new_offs)
    out += pool_body
    out += buf[chunk_base + size:]
    return bytes(out), count

def patch_manifest(buf, app_name_old, app_name_new, prefix, nprefix):
    exact = {}
    if app_name_old:
        exact[app_name_old] = app_name_new
    # discover all strings with prefix here for reporting
    nb, cnt = rebuild_pool_with_replacements(buf, exact)
    # prefix-based structured renames (in-place equal-length is not needed any more,
    # but for authorities/permission (prefix rename is also length-equal? no: washzr
    # has same len as washer) we reuse the in-place patcher AFTER pool rebuild:
    # washer(22) -> washzr(22) equal length, safe in-place.
    import axml_auth_patch
    nb2, total = axml_auth_patch.parse_rename(nb, prefix, nprefix)
    return nb2, cnt, total

if __name__ == '__main__':
    import sys
    f = sys.argv[1]
    buf = open(f, 'rb').read()
    nb2, changed, total = patch_manifest(buf,
        'com.kiwivm.security.StubApplication', 'com.midea.vm.washer.MainApplication',
        'com.midea.vm.washer', 'com.midea.vm.washzr')
    open(f, 'wb').write(nb2)
    print('exact replacements in pool:', changed, '| prefix renames:', total)
