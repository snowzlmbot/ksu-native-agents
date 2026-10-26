# KSU Native Agents — 用户要求与验证边界

- 两个独立KernelSU模块：OpenClaw、NousResearch Hermes Agent。
- 用户明确允许宿主目录读写；通过命名bind挂载访问，禁止把Android根目录用作Linux安装目录。
- 默认开机自启；后台服务只监听127.0.0.1，有鉴权；提供急停，不反复无限拉起。
- Ubuntu 26.04 LTS ARM64 / glibc，原生chroot，无需桌面，无PRoot开销。
- GitHub仓库管理与Release更新；只提交源码、固定依赖、校验清单，不提交用户数据/凭据。
- 本机 Android17 / KernelSU root / SELinux Enforcing；mount namespace可用，PID namespace不支持(EINVAL)。不改SELinux，不改系统分区，不系统化Minis。
- 目录数据保护不能等同强沙箱：UID0加宿主RW无法保证AI不误删；明确披露。模块自身不得递归清理rootfs/宿主挂载，不follow symlink进行安装/卸载。
- 自动模型调用尚需用户配置provider/model/key；不转移Minis现有凭据。
