#!/system/bin/sh
MODDIR=${0%/*}
APP=@APP@
"$MODDIR/bin/ksu-agent" "$APP" status
printf '\n管理: su -c "%s/agentctl status"\n' "$MODDIR"
printf 'OpenClaw: http://127.0.0.1:18789/\nHermes: http://127.0.0.1:9119/\n'
printf '登录凭据保存在 /data/adb/ai-containers/%s/home/LOCAL-LOGIN.txt，终端本地查看。\n' "$APP"
printf '禁用模块即可停止下次开机自启；卸载保留全部数据。\n'
