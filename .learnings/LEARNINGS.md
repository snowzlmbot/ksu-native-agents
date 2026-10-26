## 2026-10-26 KernelSU Ubuntu 构建预检
- 用户纠正：host目录明确允许读写，默认开机自启，优先Ubuntu依赖兼容性，GitHub管理。
- 不支持PID namespace (unshare CLONE_NEWPID => EINVAL)，不能声称完整namespace容器隔离。
- mount namespace可用；Android toybox mount --make-rprivate / 报bad /etc/fstab，必须调用 KSU BusyBox mount --make-rprivate /（已实测成功）。
- 不能假设旧memory项目目录在当前sandbox内仍存在，应先验证。
