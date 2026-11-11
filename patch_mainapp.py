# -*- coding: utf-8 -*-
import re, io, sys

P = r"G:\project\ujing_work\desher_proj\smali\com\midea\vm\washer\MainApplication.smali"
src = io.open(P, 'r', encoding='utf-8').read()

def replace_block(text, header, body):
    """replace `.method<header> ... .end method` block with header + body"""
    idx = text.find('.method ' + header)
    if idx < 0:
        raise SystemExit('method not found: ' + header)
    end = text.find('.end method', idx)
    if end < 0:
        raise SystemExit('end not found for ' + header)
    return text[:idx] + '.method ' + header + '\n' + body + '\n.end method' + text[end + len('.end method'):]

# 1) <clinit>: remove KwProtectSDK load
clinit_body = """    .locals 0

    return-void
"""
src = replace_block(src, 'static constructor <clinit>()V', clinit_body)

# 2) lifecycle natives -> Java bodies
super_bodies = {
 'protected attachBaseContext(Landroid/content/Context;)V':
 """    .locals 0

    invoke-super {p0, p1}, Landroid/app/Application;->attachBaseContext(Landroid/content/Context;)V

    return-void
""",
 'public onCreate()V':
 """    .locals 2

    invoke-super {p0}, Landroid/app/Application;->onCreate()V

    # keep context reference for the init chain
    invoke-virtual {p0}, Lcom/midea/vm/washer/MainApplication;->getBaseContext()Landroid/content/Context;

    move-result-object v0

    iput-object v0, p0, Lcom/midea/vm/washer/MainApplication;->mContext:Landroid/content/Context;

    # create the init handler and kick the pure-Java init chain (msg 0x65)
    new-instance v0, Lcom/midea/vm/washer/MainApplication$MyHandler;

    invoke-direct {v0, p0}, Lcom/midea/vm/washer/MainApplication$MyHandler;-><init>(Lcom/midea/vm/washer/MainApplication;)V

    iput-object v0, p0, Lcom/midea/vm/washer/MainApplication;->handler:Lcom/midea/vm/washer/MainApplication$MyHandler;

    const/16 v1, 0x65

    invoke-virtual {v0, v1}, Lcom/midea/vm/washer/MainApplication$MyHandler;->sendEmptyMessage(I)Z

    return-void
""",
}
src = replace_block(src, 'protected native attachBaseContext(Landroid/content/Context;)V', super_bodies['protected attachBaseContext(Landroid/content/Context;)V'])
src = replace_block(src, 'public native onCreate()V', super_bodies['public onCreate()V'])

plain_super = {
 'public native onTerminate()V':
 """    .locals 0

    invoke-super {p0}, Landroid/app/Application;->onTerminate()V

    return-void
""",
 'public native onTrimMemory(I)V':
 """    .locals 0

    invoke-super {p0, p1}, Landroid/app/Application;->onTrimMemory(I)V

    return-void
""",
 'public native getResources()Landroid/content/res/Resources;':
 """    .locals 0

    invoke-super {p0}, Landroid/app/Application;->getResources()Landroid/content/res/Resources;

    move-result-object v0

    return-object v0
""",
}
for k, v in plain_super.items():
    src = replace_block(src, k, v)

noops = [
 'public static native initEnvironment(Landroid/content/Context;)V',
 'private native initThirdService()V',
 'private native useMethodForUserAgree()V',
 'private native useMethodForUserAgreeOnBaseContextAttached(Landroid/content/Context;)V',
 'public native getAdvertInfoFail(ILjava/lang/String;)V',
 'public native getAdvertInfoSuc(Lcom/midea/uclean_utils_library/entity/SplashAdPlacement;)V',
 'public native initRequestAdvertInfoFail(ILjava/lang/String;)V',
 'public native initRequestAdvertInfoSuc(Ljava/util/Map;Ljava/util/Map;)V',
]
noop_body = """    .locals 0

    return-void
"""
for h in noops:
    src = replace_block(src, h, noop_body)

# 3) the MyHandler runner: needs initComplete=true at the end
# (already done inside handleMessage; our custom callback just no-ops)

io.open(P, 'w', encoding='utf-8').write(src)
print('MainApplication.smali patched ok; native count left:',
      len(re.findall(r'^\.method.*\bnative\b', src, re.M)))
