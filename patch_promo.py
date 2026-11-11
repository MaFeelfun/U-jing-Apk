# -*- coding: utf-8 -*-
"""patch_promo.py - remove ads/promos & update checks from deshelled U-jing.

Kill list:
 1. NotifyConfigInfo$NotifyConfigBean.getNotifySwitch() -> always false
    (all notify popups skipped; per-page navigation still works; forceQuit
     remote-kill dialog never shows)
 2. NotifyConfigUtils.getNotifyConfig: 5 x [updateWeexApp early-exit] -> fall
    through to HTTP path (Weex bundle hot-update disabled, pages use local bundle)
 3. IndexActivityPresenter.checkUpdate() -> no-op (app upgrade check off)
 4. MainApplicationModel.init{Home,Order,Mine}AdPlacement -> return empty list
    (banner / promo placements die at the data source; AllStatics lists empty)
 5. HomeFragmentPresenter.getCouponInfo() -> no-op (red packet / coupon popup data)
 6. RedPacketDialogUtils.createFloatImageView / initRedPacketDialog /
    showFloatImageView -> no-op (floating red-packet promo button)
"""
import io, os, re, sys

PROJ = r"G:\project\ujing_work\desher_proj"
W = r"G:\project\smali"  # unused

def load(rel):
    return io.open(os.path.join(PROJ, rel), encoding="utf-8").read()

def save(rel, txt):
    io.open(os.path.join(PROJ, rel), "w", encoding="utf-8", newline="").write(txt)

def replace_block(txt, header, body, tag=""):
    """replace the whole `.method <header> ... .end method` block"""
    needle = ".method " + header
    idx = txt.find(needle)
    if idx < 0:
        raise SystemExit("method not found [%s]: %s" % (tag, header))
    end = txt.find(".end method", idx)
    new = needle + "\n" + body.rstrip() + "\n.end method"
    return txt[:idx] + new + txt[end + len(".end method"):]

RETURN_VOID = "    .locals 0\n\n    return-void"

# ---------------------------------------------------------------- 1. notifySwitch
rel = r"smali\com\midea\vm\washer\entity\NotifyConfigInfo$NotifyConfigBean.smali"
txt = load(rel)
m = re.search(r"\.method ([^\n]*getNotifySwitch\(\)Z[^\n]*)", txt)
print("1. getNotifySwitch header:", m.group(1))
hdr = m.group(1).replace(" native ", " ")
body = "    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0"
txt = replace_block(txt, hdr, body, "notifySwitch")
save(rel, txt)

# ---------------------------------------------------------------- 2. weex hot-update
rel = r"smali\com\midea\vm\washer\utils\NotifyConfigUtils.smali"
txt = load(rel)
pat = re.compile(
    r"invoke-interface \{p3, p2\}, Lcom/midea/vm/washer/ui/ui_interface/"
    r"NotifyConfigInterface;->updateWeexApp\(Ljava/lang/String;\)V\r?\n\s*return-void")
n = len(pat.findall(txt))
print("2. updateWeexApp early-exit blocks:", n)
assert n == 5, n
txt = pat.sub("goto/16 :cond_5", txt)
save(rel, txt)

# ---------------------------------------------------------------- 3. checkUpdate
rel = r"smali\com\midea\vm\washer\ui\presenter\IndexActivityPresenter.smali"
txt = load(rel)
m = re.search(r"\.method ([^\n]*checkUpdate\(\)V[^\n]*)", txt)
print("3. checkUpdate header:", m.group(1))
txt = replace_block(txt, m.group(1), RETURN_VOID, "checkUpdate")
save(rel, txt)

# ---------------------------------------------------------------- 4. placements
rel = r"smali\com\midea\vm\washer\ui\model\MainApplicationModel.smali"
txt = load(rel)
EMPTY_LIST = ("    .locals 1\n\n"
              "    new-instance v0, Ljava/util/ArrayList;\n\n"
              "    invoke-direct {v0}, Ljava/util/ArrayList;-><init>()V\n\n"
              "    return-object v0")
for name in ("initHomeAdPlacement", "initOrderAdPlacement", "initMineAdPlacement"):
    m = re.search(r"\.method ([^\n]*" + name + r"\(Lorg/json/JSONObject;\)Ljava/util/List;[^\n]*)", txt)
    print("4.", name, "->", m.group(1))
    txt = replace_block(txt, m.group(1), EMPTY_LIST, name)
save(rel, txt)

# ---------------------------------------------------------------- 5. coupon push
rel = r"smali\com\midea\vm\washer\ui\presenter\HomeFragmentPresenter.smali"
txt = load(rel)
m = re.search(r"\.method ([^\n]*getCouponInfo\(\)V[^\n]*)", txt)
print("5. getCouponInfo header:", m.group(1))
txt = replace_block(txt, m.group(1), RETURN_VOID, "getCouponInfo")
save(rel, txt)

# ---------------------------------------------------------------- 6. red packet float
rel = r"smali\com\midea\vm\washer\utils\RedPacketDialogUtils.smali"
txt = load(rel)
for sig in ("createFloatImageView(Lcom/midea/vm/washer/base/BaseAppCompatActivity;)V",
            "initRedPacketDialog(Landroid/content/Context;Lcom/midea/vm/washer/base/BaseAppCompatActivity;Z)V",
            "showFloatImageView()V"):
    m = re.search(r"\.method ([^\n]*" + re.escape(sig) + r"[^\n]*)", txt)
    print("6.", sig.split("(")[0], "->", m.group(1))
    txt = replace_block(txt, m.group(1), RETURN_VOID, sig)
save(rel, txt)

print("ALL PATCHES APPLIED")
