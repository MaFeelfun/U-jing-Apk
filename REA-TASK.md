# REA-TASK

## 目标(用户已回答 STEP 1 的 4 个问题)
1. 目标: Android APK —— 手机上的「U净」APP
2. 位置: 通过 adb 连接的手机 <adb-wifi-addr>(需要先 pull APK 到本机)
3. 要理解的行为: APP 中各种广告/推广入口的来源;APP 的可去除性(扫一扫、吹风两个核心功能要保留);启动时/设置里的更新检测逻辑
4. 最终交付: (C类) 修改后的 APK —— 去除广告与推广入口、仅保留「扫一扫」与「吹风」功能、禁用更新检测 → 重打包(重新对齐+签名)→ 安装回手机

## 修改清单
- [ ] 去除广告/推广(首页弹窗、Banner 广告、营销活动入口等)
- [ ] 仅保留 扫一扫 + 吹风 功能
- [ ] 禁用更新检测(升级弹窗/检查更新接口调用)
- [ ] 重打包(apktool b → zipalign → 签名)
- [ ] adb 安装到 <adb-wifi-addr>

## 环境记录
- 工作目录: G:\project\U净 (Windows)
- 设备: <adb-wifi-addr> (adb over WiFi)

## 进度
- REA doctor 完成:OpenCode MCP 注册损坏(客户端配置是坏 JSON),按官方恢复指南改用 REA CLI 继续
- 已定位目标: com.midea.vm.washer (U净) v2.4.18 versionCode 20418, aapt 验证 application-label='U净'
- 已拉取到本地: base.apk 107,499,274 bytes, sha256=0adcfc7caefbae96c0131db89f09b5fe046c18876eb5b50acdba0dd6db61f691
- 工作副本: G:\project\ujing_work (纯 ASCII 路径,避免 aapt 中文路径问题)

## 阶段结论(分析中)
1. APK 为 KiwiVM/entryexpro 系加固壳: classes.dex 仅 4 个 stub 类(com.kiwivm.security.* + kdp.AR), 真实代码在运行时由 native(libentryexpro/libzeus) 解密内存加载
2. 壳字符串为逐字符 XOR(key 循环) —— Xkd.l(key, bytes)
3. 脚本方案: 用 frida-gadget 17.24.3 注入 StubApplication.<init>(lib 名 svc233, 端口 32233), 已完成: dumpapp-signed.apk 安装成功, gadget 监听成功, 壳未做签名自检拦截(进程存活, splash 正常显示 UJING 画面)
4. UI 全部在未加密 Weex JS bundle: assets/{washer,hairdryer,shower,water,airconditioner,quickwindow,h5}/*.js + main.js(仅 Weex 框架) + weex-main-jsfm.js
5. JS 中未见专门 ad SDK;  banner/活动/红包/优惠券数据由服务端下发到通用组件; advData 为 BLE 广播(advertisData), 与广告无关
6. 待脱壳后确认: 更新检查逻辑、开屏广告逻辑、首页推广数据渲染入口

## 进行中
- frida-dexdump 后台抓内存 dex → G:\project\ujing_work\dexout
- baksmali 工具已就绪 (baksmali.jar + deps)

## 下一步
next step: 5 (baksmali dumped dex → 溯源广告/推广/更新检测 → 编写补丁)
