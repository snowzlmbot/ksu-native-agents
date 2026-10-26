# KSU Native Agents

两个独立的 KernelSU 模块：Ubuntu 26.04.1 ARM64/glibc 原生 chroot 中运行 OpenClaw 与 Hermes Agent。

## 设计

- 默认开机自启；每个模块独立 rootfs、home、workspace、运行日志、端口和登录凭据。
- 容器内真实 UID 0；默认 `/host/data`、`/host/storage` 等宿主路径可读写。
- `/data/adb` 默认遮蔽；通过 `/data/adb/ai-containers/<app>/mounts.tsv` 显式增加路径映射：`label<TAB>/absolute/path`。映射源由 root 解析并拒绝 `/`、`/proc`、`/sys`、`/dev`；映射 `/data/adb` 会告警并赋予 KernelSU 控制数据权限。
- 不使用 system overlay、`post-fs-data.sh`、`sepolicy.rule` 或全局 SELinux 修改。挂载只在 private mount namespace 中。
- 运行时启用 Landlock ABI 6 的 signal/abstract Unix scope、capability drop、seccomp、独立 cgroup v2；本机没有 PID namespace，因此这不是恶意代码的强隔离沙箱。
- 卸载只请求停止，不删除 rootfs、home、workspace、配置、密钥、日志或宿主映射源。

## 数据位置

```text
/data/adb/ai-containers/openclaw/
/data/adb/ai-containers/hermes/
```

模块目录被 KernelSU 生命周期管理，不存用户数据。升级在新的 `versions/<version>` 目录解包并校验后切换 `current`；旧版本保留。

## 运行验收

OpenClaw：`127.0.0.1:18789/healthz` 与 `/readyz`；无模型 key 可验收进程、配置、SQLite/native、loopback、锁、优雅关闭。

Hermes：`127.0.0.1:9119/api/status` 应为 `overall=ok`、`auth_required=true`、`auth_providers=["basic"]`；未登录 `/api/config` 应为 401。

模型服务商 API key 不内置、不提交 GitHub；首次启动生成的本机凭据在对应 `home/LOCAL-LOGIN.txt`，权限 0600。

## 构建

构建器需要已验证的 Ubuntu ARM64 rootfs tar.xz，以及静态 ARM64 `build/ksu-agent`：

```sh
make
python3 scripts/package.py --app openclaw --rootfs dist/openclaw-rootfs.tar.xz --binary build/ksu-agent --output dist/ksu_openclaw-0.1.0-rc1.zip
python3 scripts/package.py --app hermes --rootfs dist/hermes-rootfs.tar.xz --binary build/ksu-agent --output dist/ksu_hermes-0.1.0-rc1.zip
```

`package.py` 会拒绝绝对路径、`..`、设备节点和 FIFO tar 成员，生成 KernelSU ZIP、SHA256 清单和 SBOM 元数据。不要把 `home/`、`.env`、token、数据库、聊天记录或 rootfs 开发缓存提交到仓库。

## 限制

Android 内核禁用了 PID namespace；网络命名空间也不由本模块创建，loopback 端口仍属于设备本机。root + 宿主读写意味着被授权的 Agent/技能可以修改或删除映射目录，必须另行备份重要数据。
