# axml_auth_patch.py - structurally rename authorities/permission values containing a prefix.
# Walks binary AXML chunks; strings in the pool are UTF-16LE (this app's manifest).
import struct

def parse_rename(buf, prefix, nprefix):
    """returns (new_bytes, count_renamed) renaming values of:
       - android:authorities (provider)
       - android:name of <permission>, <uses-permission>, <permission-group>
       - android:permission attr values (usage sites)
       - android:name of <meta-data> when it embeds the prefix
    Class names (activity/service/application/provider android:name) untouched."""
    old16 = prefix.encode('utf-16-le')
    new16 = nprefix.encode('utf-16-le')
    assert len(old16) == len(new16)
    out = bytearray(buf)
    total = 0

    # string pool: first chunk
    off = 8  # RES_XML header
    typ, hdrsz, size = struct.unpack_from('<HHI', buf, off)
    assert typ == 0x0001, hex(typ)  # RES_STRING_POOL_TYPE
    count, styleCount, flags, stringsStart, stylesStart = struct.unpack_from('<IIIII', buf, off + 8)
    is_utf8 = bool(flags & (1 << 8))
    assert not is_utf8, 'expected utf-16 pool'
    base = off + stringsStart
    offs = struct.unpack_from('<%dI' % count, buf, off + 28)
    def s(idx):
        if idx == 0xFFFFFFFF: return None
        p = base + offs[idx]
        ln, = struct.unpack_from('<H', buf, p)  # utf16 len (not checking extended)
        st = p + 2
        raw = buf[st:st + ln * 2]
        return raw.decode('utf-16-le'), st, raw

    def find_starts(buf, needle):
        idxs = []
        start = 0
        while True:
            i = buf.find(needle, start)
            if i < 0: break
            idxs.append(i)
            start = i + 1
        return idxs

    def rename_at(st, raw):
        # in-place within out[]
        st_o = st  # same layout in out
        if bytes(out[st:st + len(old16)]) == old16:
            pass
        else:
            return False
        out[st:st + len(old16)] = new16
        return True

    # build map from old substring occurrence offset -> patch
    # We'll walk elements and decide renames by attribute semantics.
    i = off + size
    elements = []
    end_of_file = len(buf)
    p = off + size
    while p + 8 <= end_of_file - 0:
        t, hs, sz = struct.unpack_from('<HHI', buf, p)
        if sz == 0: break
        if t == 0x0102:  # start element
            lineno, comment = struct.unpack_from('<II', buf, p + 8)
            q = p + 16
            elem_ns, elem_name, attrStart, attrSize, attrCount = struct.unpack_from('<IIHHH', buf, q)
            elem_name_s = s(elem_name)[0]
            for a in range(attrCount):
                ab = q + attrStart + a * attrSize
                ans, aname, araw = struct.unpack_from('<III', buf, ab)
                avsz, avres0, avtyp = struct.unpack_from('<HBB', buf, ab + 12)
                adata, = struct.unpack_from('<I', buf, ab + 16)
                nm = s(aname)[0]
                val = s(araw)[0] if araw != 0xFFFFFFFF else None
                if val is None:
                    continue
                if prefix not in val:
                    continue
                rename_it = False
                if nm == 'authorities':
                    rename_it = True
                elif nm == 'permission':
                    rename_it = True
                elif nm == 'name' and elem_name_s in ('permission', 'uses-permission', 'permission-group', 'meta-data'):
                    rename_it = True
                if rename_it:
                    # string data location: via raw value -> string pool offset
                    txt, st, raw = s(araw)
                    if rename_at(st, raw):
                        total += 1
        p += sz
    return bytes(out), total

if __name__ == '__main__':
    import sys
    f = sys.argv[1]
    buf = open(f, 'rb').read()
    nb, n = parse_rename(buf, 'com.midea.vm.washer', 'com.midea.vm.washzr')
    open(f, 'wb').write(nb)
    print('renamed', n)
