# v0.1.0-rc11 — WebUI、原生终端与运行时修复

本 Release 附有 **4 个真正可下载的 ZIP**，不是只有源码标签。

## 选择哪个包

| 应用 | 已安装本项目且保留完整 Ubuntu 环境 | 全新安装 |
|---|---|---|
| OpenClaw | `ksu_openclaw-0.1.0-rc11-update.zip`（约 73 KB） | `ksu_openclaw-0.1.0-rc11-full.zip`（约 304 MiB） |
| Hermes | `ksu_hermes-0.1.0-rc11-update.zip`（约 73 KB） | `ksu_hermes-0.1.0-rc11-full.zip`（约 642 MiB） |

升级包不包含 Ubuntu，只复用 `/data/adb/ai-containers/<app>/current` 指向的完整环境；缺少环境会拒绝安装。完整包离线包含 Ubuntu。不要卸载或删除运行数据再刷升级包。使用 KernelSU Manager 安装，按 Manager 提示重启激活。**本次发布不自动刷机、不替用户重启。**

## 更新内容

- 两个模块内置 `webroot/index.html`，服务状态、启停、模型路由设置、MT/Termux 命令复制和存储检查。
- 修复 WebUI 普通 script 中的非法顶层 `await`，并验证原生桥接回调。
- 修复 `termux model set` 多参数转发；新增 `panel` 文本控制面板、`native` 原生 CLI 透传。
- 模型配置通过应用自身 config 命令；显示配置只输出路由白名单字段，不输出 Gateway Token 或 API Key。密钥在交互终端 `model key` 或 `model wizard` 不回显输入，不写进 argv。
- 安装包带 `runtime/` 并原子同步到实际 Ubuntu；避免“ZIP 有新文件而复用 rootfs 仍运行旧脚本”。
- Hermes PM runtime 链接初始化顺序与元数据修复；启用内置简体中文 `hermes-locale=zh`。
- 修复 fresh install 合并 `/usr` 的标准链接；恢复 `skip_mount`；明确所有入口执行权限。
- 停止等待 PID 退出；启动时对超过 8 MiB 的 supervisor 日志轮转。缓存清理改成手动、有界、不跟随软链接的专属缓存清理，取消开机递归删除。
- 卸载保留 home、会话、配置、密钥、工作区、rootfs 与宿主映射源。

## MT / Termux（需先 `su`，对应 App 获准 Root）

```sh
/data/adb/modules/ksu_openclaw/termux panel
/data/adb/modules/ksu_hermes/termux panel

/data/adb/modules/ksu_openclaw/termux model wizard
/data/adb/modules/ksu_hermes/termux model wizard

/data/adb/modules/ksu_openclaw/native --version
/data/adb/modules/ksu_hermes/native --version
```

端口仍为 OpenClaw `127.0.0.1:18789`、Hermes `127.0.0.1:9119`；保留鉴权。

## 校验与真实边界

- 附 `SHA256SUMS`、`release-validation.json`、`package-validation.json`。
- 验收范围：shell/Python/JS 语法、模型输入校验、WebUI 原生桥接夹具、MT/Termux 参数转发、四个 ZIP CRC 与全部文件哈希、运行文件源码一致性。
- 新 rc11 **没有在用户手机上安装并重启验收**；不能将此前本机热补丁的健康结果等同于 rc11 全功能端到端验收。
- Hermes 使用官方内置中文翻译资源，不改模型回复/用户文件/第三方插件/外部英文文档；没有宣称所有硬编码提示都已逐项译完。
- 未配置模型凭据时不能验收真实推理；本发布未执行付费模型调用，也未验证所有第三方插件。
- 仍要求 ARM64、KernelSU、私有挂载 namespace、Landlock ABI≥6、可用 cgroup v2。PID namespace 不受支持的设备不是强隔离沙箱。Root+宿主目录 RW 不能保证任意 Agent 命令绝不误删，重要数据需自行备份。
