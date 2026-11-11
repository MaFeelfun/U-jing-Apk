# -*- coding: utf-8 -*-
"""patch_promo2.py - kill remaining promo slots & stuck 'loading' placeholders.

Sources identified:
 - home banner_Layout (0x7f09008d): default bg not_net_default_image1
   ("正在加载中，请稍后...") shows forever because placement data is empty.
 - home welfareCenter grid: initRecommendAdapter() shows grid + "加载中"
   placeholder cells (HomeFragment$12.convert :cond_a).
 - mine dynamic_content_cards (0x7f090188): 3 GifImageViews whose default bg
   IS the "加载中..." mascot placeholder (place_holder_mine_1/2).
 - mine feature_ads (0x7f0901a6): 4th icon slot, blank without ad data.

NOT touched: setApplicationInfo() = core feature grid (washer/water/shower/
airconditioner/hairdryer home.js entries).
"""
import io, os, re

PROJ = r"G:\project\ujing_work\desher_proj"
FRAG = "Lcom/midea/vm/washer/ui/fragment/{};"

def load(rel):
    return io.open(os.path.join(PROJ, rel), encoding="utf-8").read()

def save(rel, txt):
    io.open(os.path.join(PROJ, rel), "w", encoding="utf-8", newline="").write(txt)

def get_method(txt, header_re):
    m = re.search(r"\.method " + header_re + r"\r?\n[\s\S]*?\.end method", txt)
    if not m:
        raise SystemExit("method not found: " + header_re)
    return m

def hide_code(fragment_class, ids):
    """smali that hides the given view ids at end of initView (uses v0/v1)."""
    out = []
    for n, vid in enumerate(ids):
        lbl = ":cond_hide%d" % n
        out.append(
            "invoke-virtual {p0}, %s->getView()Landroid/view/View;\n" % fragment_class +
            "move-result-object v0\n" +
            "if-eqz v0, %s\n" % lbl +
            "const v1, 0x%x\n" % vid +
            "invoke-virtual {v0, v1}, Landroid/view/View;->findViewById(I)Landroid/view/View;\n" +
            "move-result-object v0\n" +
            "const/16 v1, 0x8\n" +
            "invoke-virtual {v0, v1}, Landroid/view/View;->setVisibility(I)V\n" +
            "%s\n" % lbl
        )
    return "".join(out)

# ------------------------------------------------ 1. home welfareCenter grid
rel = r"smali\com\midea\vm\washer\ui\fragment\HomeFragment.smali"
txt = load(rel)
m = get_method(txt, r"private initRecommendAdapter\(Ljava/util/List;Z\)V")
print("1. initRecommendAdapter:", len(m.group()), "chars -> return-void")
txt = txt[:m.start()] + \
    ".method private initRecommendAdapter(Ljava/util/List;Z)V\n    .locals 0\n\n    return-void\n.end method\n" + \
    txt[m.end():]

# ------------------------------------------------ 2. home banner_Layout hide
m = get_method(txt, r"protected initView\(Landroid/view/View;\)V")
block = m.group()
j = block.rfind("return-void")
assert j > 0
code = hide_code(FRAG.format("HomeFragment"), [0x7f09008d])
block = block[:j] + code + block[j:]
txt = txt[:m.start()] + block + txt[m.end():]
save(rel, txt)
print("2. HomeFragment.initView: banner_Layout hidden")

# ------------------------------------------------ 3. mine promos hide
rel = r"smali\com\midea\vm\washer\ui\fragment\MineFragment.smali"
txt = load(rel)
m = get_method(txt, r"protected initView\(Landroid/view/View;\)V")
block = m.group()
j = block.rfind("return-void")
assert j > 0
code = hide_code(FRAG.format("MineFragment"),
                 [0x7f090188, 0x7f0901a6])  # dynamic_content_cards, feature_ads
block = block[:j] + code + block[j:]
txt = txt[:m.start()] + block + txt[m.end():]
save(rel, txt)
print("3. MineFragment.initView: dynamic_content_cards + feature_ads hidden")

print("ALL PATCHES APPLIED")
