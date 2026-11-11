# axml_pkg_patch.py - rename manifest @package attribute in binary AXML by in-place string pool edit (same length swap).
import struct, sys

def parse_string_pool(d):
    # returns (chunk_off, entries) where entries[i] = (start,end) byte slice EXCLUDING the two null terminators, plus raw info
    off = 8  # file header size (res header 8 bytes)
    while off < len(d):
        ctype, hsz, size = struct.unpack_from('<HHI', d, off)
        if ctype == 0x0001:  # STRING_POOL
            strs, styles, flags, stringsStart, stylesStart = struct.unpack_from('<IIIII', d, off+8)
            utf8 = bool(flags & 0x100)
            base = off + stringsStart
            entries = []
            for i in range(strs):
                so = struct.unpack_from('<I', d, off + 28 + i*4)[0]
                p = base + so
                if utf8:
                    u16len = d[p]; p += 1
                    if u16len & 0x80:
                        u16len = ((u16len & 0x7f) << 7) | (d[p]); p += 1
                    u8len = d[p]; p += 1
                    if u8len & 0x80:
                        u8len = ((u8len & 0x7f) << 7) | (d[p]); p += 1
                    s = d[p:p+u8len].decode('utf-8')
                    start = p
                    end = p + u8len
                else:
                    l1 = struct.unpack_from('<H', d, p)[0]; p += 2
                    if l1 & 0x8000:
                        l2 = struct.unpack_from('<H', d, p)[0]
                        l1 = ((l1 & 0x7fff) << 16) | l2
                        p += 2
                    start = p
                    nbytes = l1 * 2
                    end = start + nbytes
                    s = d[start:end].decode('utf-16le')
                entries.append({'start': start, 'end': end, 'str': s, 'hdr_end': end})
            return off, size, entries
        off += size
    return None

def find_package_attr_index(d):
    # find start-element chunk 0x0102 named 'manifest'; read attrs: find attr with name 'package' (res-name index of string 'package')
    _, _, entries = parse_string_pool(d)
    pkgidx = [i for i, e in enumerate(entries) if e['str'] == 'package']
    if not pkgidx:
        raise SystemExit('no pool string named package')
    pkgidx = pkgidx[0]
    mcidx = [i for i, e in enumerate(entries) if e['str'] == 'manifest']
    if not mcidx:
        raise SystemExit('no manifest elem')
    mcidx = mcidx[0]

    off = 8
    while off < len(d):
        ctype, hsz, size = struct.unpack_from('<HHI', d, off)
        if ctype == 0x0102:  # START_ELEMENT
            ns, name = struct.unpack_from('<II', d, off+16)
            attrStart, attrSize, attrCount = struct.unpack_from('<HHH', d, off+24)
            if name == mcidx:
                # attributes base: node header (hsz=16: hdr 8 + line 4 + comment 4) + attrStart
                for ai in range(attrCount):
                    a0 = off + hsz + attrStart + ai*attrSize
                    aname = struct.unpack_from('<I', d, a0+4)[0]
                    tv = a0 + 12
                    szt = struct.unpack_from('<H', d, tv)[0]
                    res0 = d[tv+2]
                    vtype = d[tv+3]
                    data = struct.unpack_from('<I', d, tv+4)[0]
                    if aname == pkgidx and vtype == 0x03:
                        return data
        off += size
    raise SystemExit('package attr not found')

def patch(src, dst, newpkg):
    d = bytearray(open(src, 'rb').read())
    old = 'com.midea.vm.washer'
    assert len(newpkg) == len(old), 'length mismatch'
    so, ssize, entries = parse_string_pool(d)
    idx = find_package_attr_index(d)
    e = entries[idx]
    assert e['str'] == old, 'unexpected %r' % e['str']
    nbytes = len(newpkg) * 2
    d[e['start']:e['end']] = newpkg.encode('utf-16le')
    open(dst, 'wb').write(bytes(d))
    print('patched package ->', newpkg, 'pool entry', idx, '@', e['start'])

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    newpkg = sys.argv[3]
    patch(src, dst, newpkg)
