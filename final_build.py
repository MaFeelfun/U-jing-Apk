# -*- coding: utf-8 -*-
"""final_build.py - build deshelled U-jing APK from stock base.apk"""
import zipfile, os, sys, struct

WORK = r"G:\project\ujing_work"
STOCK = os.path.join(WORK, "apks", "com.midea.vm.washer", "base.apk")
DEXSRC = os.path.join(WORK, "desher_raw.apk")
MANIFEST = os.path.join(WORK, "manifest_final.axml")
OUT = os.path.join(WORK, "apks", "washzr_deshelled.apk")

SKIP_EXACT = set()
def skip_class(n):
    return (n.startswith('lib/') and n.endswith('.so') and
            ('libKwProtectSDK.so' in n or 'libkadp.so' in n)) \
        or n == 'assets/kwpt.lincense' \
        or (n.endswith('.dex') and n.startswith('classes'))

with zipfile.ZipFile(STOCK) as src, zipfile.ZipFile(DEXSRC) as dexapk:
    newdex = {n: dexapk.read(n) for n in dexapk.namelist() if n.endswith('.dex')}
    print('new dexes:', {k: len(v) for k, v in newdex.items()})

    out = zipfile.ZipFile(OUT, 'w', zipfile.ZIP_STORED)
    # copy stock entries, with substitutions
    man = open(MANIFEST, 'rb').read()
    placed_dex = 0
    for info in src.infolist():
        n = info.filename
        if n == 'AndroidManifest.xml':
            ni = zipfile.ZipInfo(n, (2020, 1, 1, 0, 0, 0))
            ni.compress_type = info.compress_type
            out.writestr(ni, man)
            continue
        if n.endswith('.dex') and n.startswith('classes') and n in newdex:
            ni = zipfile.ZipInfo(n, (2020, 1, 1, 0, 0, 0))
            ni.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(ni, newdex[n])
            newdex.pop(n)
            placed_dex += 1
            continue
        if skip_class(n):
            print('skip:', n)
            continue
        data = src.read(n)
        ni = zipfile.ZipInfo(n, (2020, 1, 1, 0, 0, 0))
        ni.compress_type = info.compress_type
        ni.external_attr = info.external_attr
        out.writestr(ni, data)
    # any dexes that did not exist in stock: append
    for n, data in newdex.items():
        ni = zipfile.ZipInfo(n, (2020, 1, 1, 0, 0, 0))
        ni.compress_type = zipfile.ZIP_DEFLATED
        out.writestr(ni, data)
    out.close()
print('placed dexes:', placed_dex)
print('built:', OUT, os.path.getsize(OUT))
