# Threat model / 安全边界

本项目是具有宿主文件读写能力的 Root 运行环境，不是面向恶意代码的强隔离沙箱，也不承诺绝不丢数据。

## 模块自身避免的危险行为
- 不包含 system/、post-fs-data.sh、sepolicy.rule、system.prop；不更改系统分区/SELinux/Android目录结构。
- 所有运行挂载仅在新建 mount namespace 内，第一步将 `/` 改为 recursively private；不在 init 命名空间挂载。
- 两个独立 rootfs；固定绝对状态目录；逐级拒绝软链接；宿主目录只映射到 `/host/*`。
- 不递归卸载/删除 rootfs 或宿主目录；卸载脚本仅停止对应程序并保留全部数据。
- 更新采用新 versions/<版本> 目录，校验成功再原子切 current；旧版本保留，禁止后台自动更新。
- 默认开机自启，但可用 KSU 禁用和 NO_AUTOSTART 急停；失败最多4次，端口仅loopback；不kill端口占用者。
- 缩减capabilities并用seccomp拒绝挂载/卸载/切命名空间/chroot/reboot/装载内核模块等，保留uid0和文件DAC权限。
- 不向容器映射宿主block设备或Android su入口。

## 不保证的事项
- 本机没有PID/User/IPC namespace，进程网络等未完全隔离；同UID进程交互及部分/proc元数据可见。
- 有RW的宿主目录可能被AI/用户/第三方技能删除、覆盖、改权限；必须自行备份。
- Android系统分区若本来只读，本项目不解锁/重新挂载；SELinux/文件加密未解锁的目录不可保证访问。
- 外网API、插件/MCP/供应链属于额外信任；未配置模型key不能完成AI端到端测试。

默认 `/host/data/adb` 遮蔽，避免模块修改自身及其他Root模块；需要访问该路径可显式新增命名目录映射，且应自行承担风险。此措施不是安全边界，不能把uid0解释为强沙箱。
