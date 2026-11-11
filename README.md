# U净-Lite — 「U净」共享洗衣 App 去广告改造

> ⚠️ **免责声明**：本项目为个人学习 Android 逆向工程与 smali 补丁技术的研究记录，仅供技术交流。
> 仓库**不包含、不分发**任何 APK、反编译代码或资源文件——所有产物均需使用者自行从合法渠道获取原版应用后按本文流程生成。
> 「U净」及相关商标、代码版权归原权利方所有。请勿用于商业用途，请在法律允许的范围内使用，后果自负。

---

## 项目简介

对美的「U净」（共享洗衣 App，原包名 `com.midea.vm.washer`，分析版本 2.4.18）做的一轮去广告/去推广/禁更新改造。

原版 App 采用商业加固壳保护，本项目通过运行时脱壳取得真实代码，再以 smali 补丁方式精准移除广告与推广链路，最终重新组包、签名、安装。

### 改造效果

| 类别 | 处理 | 方式 |
|---|---|---|
| 首页/页内轮播 Banner | ❌ 移除 | 广告 placement 接口解析置空（数据源头） |
| 弹窗活动推广图 | ❌ 移除 | `notifySwitch` 恒 false，弹窗分支全部跳过 |
| 首页「正在加载中」空 Banner 条 | ❌ 移除 | 占位容器隐藏 |
| 首页「福利中心」推广网格 | ❌ 移除 | 网格适配器构建方法 no-op |
| 「我的」页推广卡（专题/常见问题/福利专区） | ❌ 移除 | 占位容器隐藏 |
| 「我的」页第 4 个推广图标位 | ❌ 移除 | 容器隐藏 |
| 悬浮红包按钮/红包弹窗 | ❌ 移除 | 红包浮窗与弹窗工具类 no-op + 优惠券推送数据源关闭 |
| 「发现新版本」更新弹窗 | ❌ 禁用 | 更新检测方法 no-op |
| Weex 包热更新 | ❌ 禁用 | 热更新提前退出分支改为继续走本地包 |
| 服务端远程强制退出开关（forceQuit） | ❌ 顺带移除 | 随 notifySwitch 关闭 |
| **扫一扫 / 吹风 / 洗衣 / 烘干等核心功能** | ✅ 完整保留 | 功能宫格数据源未动 |
| 首页快捷窗口（Weex） | ✅ 保留 | 本地 JS 包渲染，正常功能 |

---

## 技术要点

### 流程总览

```
自备原版 base.apk
   │
   ├─ ① 脱壳（加固壳运行时 dump，产物为真实 dex）
   ├─ ② baksmali 反编译 → smali 工程（desher_proj）
   ├─ ③ 应用补丁（patch_mainapp / patch_promo / patch_promo2 / axml_*）
   ├─ ④ apktool b 回编译 → desher_raw.apk
   ├─ ⑤ final_build.py：以原版 APK 为底版替换 dex/manifest、剔除壳 so
   ├─ ⑥ zipalign + apksigner 签名
   └─ ⑦ adb 安装
```

### 脱壳方案（简述）

- 壳的 stub dex 与多 ABI 的保护 so 在组包阶段被整体剔除（`final_build.py` 的 skip 规则），manifest 的 `application` 指向真实 Application。
- 原 Application 中的十余个加固壳 native 初始化方法全部以等价 Java/smali 逻辑重写（见 `patch_mainapp.py`）。
- 旧 Splash 流程（协议页/开屏广告/壳检测）整体重写：直接轮询初始化完成标志后进入主界面。

### 广告链路打击点

| 打击点 | 位置 | 作用 |
|---|---|---|
| `init{Home,Order,Mine}AdPlacement` | `MainApplicationModel` | 返回空列表，三类广告位数据源死亡 |
| `getNotifySwitch()` | `NotifyConfigInfo$NotifyConfigBean` | 恒 false，通知弹窗跳过且页面导航不受影响 |
| `updateWeexApp` 提前退出分支 ×5 | `NotifyConfigUtils.getNotifyConfig` | 改为继续走 HTTP 请求 → 禁 Weex 热更新 |
| `checkUpdate()` | `IndexActivityPresenter` | 更新检测 no-op |
| `getCouponInfo()` | `HomeFragmentPresenter` | 红包/优惠券弹窗数据源关闭 |
| `createFloatImageView` / `initRedPacketDialog` / `showFloatImageView` | `RedPacketDialogUtils` | 悬浮红包浮窗 no-op |
| `initRecommendAdapter(List, Z)` | `HomeFragment` | 福利中心网格（含「加载中」占位格）不再构建 |
| `initView` 追加隐藏 `banner_Layout` | `HomeFragment` | 首页空 Banner 占位条隐藏 |
| `initView` 追加隐藏 `dynamic_content_cards` / `feature_ads` | `MineFragment` | 「我的」页推广卡与空白图标位隐藏 |

### 特意保留的链路（不能动）

- `HomeModel.setApplicationInfo` —— 首页功能宫格（洗衣机/净水/热水器/空调/吹风），核心功能入口
- `getEntryConfigByUserId` —— H5 路由开关，Weex 页面导航必需
- `notifyConfig` 请求链本身 —— 功能页打开的门控（只能动 `getNotifySwitch`，不能整体 no-op）
- 快捷窗口 Weex（`quickwindow/home.js`）—— 订单快捷卡片，正常功能
- 「我的」页红包/优惠券数字展示 —— 用户资产信息

---

## 仓库内容

```
├── README.md               本文档
├── .gitignore              排除 APK/反编译产物/签名库等
├── REA-TASK.md             逆向过程工作记录（任务拆解与阶段结论）
├── patch_mainapp.py        Application 壳方法 native→Java 重写补丁
├── patch_promo.py          广告清理补丁 v1（placement/弹窗/更新/红包）
├── patch_promo2.py         广告清理补丁 v2（占位模块/推广卡隐藏）
├── final_build.py          组包：原版 APK 底版 + 新 dex/manifest
├── axml_app_patch.py       AXML 补丁：application 类名重指向
├── axml_auth_patch.py      AXML 补丁：provider authorities/permission 前缀改名
└── axml_pkg_patch.py       AXML 补丁：package 属性改名
```

> smali 工程与 APK 产物**不进仓库**（见 `.gitignore`）：前者是原厂专有代码的衍生品，不宜公开分发；后者体积巨大。

---

## 复现步骤

### 环境依赖

- Python 3.10+
- apktool 2.9.3
- Android build-tools（zipalign / apksigner / aapt2）
- JDK 8+
- 自备签名密钥（`keytool` 生成即可，**不要使用仓库外的任何他人密钥，也不要提交自己的密钥**）
- 自备合法获取的原版 APK

### 步骤示例

```bash
# 1. 解包原版 APK（得到 smali 工程，路径请按需调整）
java -jar apktool.jar d base.apk -o desher_proj

# 2. 应用补丁（脚本内的工程路径需先改为你的实际路径）
python patch_mainapp.py
python patch_promo.py
python patch_promo2.py
python axml_app_patch.py && python axml_auth_patch.py && python axml_pkg_patch.py

# 3. 回编译
java -jar apktool.jar b desher_proj -o desher_raw.apk

# 4. 组包（以原版 APK 为底版，替换 dex/manifest、剔除壳 so）
python final_build.py

# 5. 对齐 + 签名（KS/KS_PASS/ALIAS 换成你自己的）
zipalign -f -p 4 out.apk out-aligned.apk
apksigner sign --ks mykey.jks --ks-pass pass:你的口令 --ks-key-alias myalias --out final.apk out-aligned.apk

# 6. 安装（示例为 vivo 设备；无线调试地址会漂移，注意重连）
adb connect <设备地址>
adb push final.apk /data/local/tmp/app.apk
adb shell pm install -r -i com.vivo.appstore /data/local/tmp/app.apk
```

> 补丁脚本按「精确方法头定位 + 整方法替换」编写，方法不存在或结构不符会直接报错退出，不会静默跳过。

---

## 踩坑记录

1. **smali `native` 关键字残留**：把 native 方法改为 Java 实现时，若方法头仍保留 `native`，smali 会忽略方法体——补丁后必须确认 0 个 native。
2. **CRLF 行尾**：工程文件为 CRLF，精确文本匹配需用正则 `\r?\n`。
3. **寄存器复用导致 VerifyError**：重构方法块时，被覆盖的寄存器可能仍被后续代码以不同类型使用（如 `'this' argument not instance of...`），需给关键引用分配专用寄存器。
4. **`const/4` 字面量范围**：只有 -8~7，设置 `setVisibility(0x8)` 这类值要用 `const/16`。
5. **notifyConfig 是导航门控**：功能页（washer/water/shower…）打开依赖该请求回调，只能关弹窗开关，不能 no-op 整个请求。
6. **vivo 无线调试地址漂移**：每次重连先 `adb connect <新地址>`；安装报 stale baseline.prof 告警属正常，以 `pm path <包名>` 验证。
7. **测试包与商店版并行**：改包名安装，避免干扰手机上商店安装的原版。

---

## License

补丁脚本部分以 MIT License 发布。原版应用的代码、资源、商标归原权利方所有，不在本仓库授权范围内。
