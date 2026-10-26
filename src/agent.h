#ifndef KSU_AGENT_H
#define KSU_AGENT_H
#define _GNU_SOURCE
#include <sys/types.h>
#define BASE "/data/adb/ai-containers"
#define MODBASE "/data/adb/modules"
#define APP_OPENCLAW "ksu_openclaw"
#define APP_HERMES "ksu_hermes"
void die(const char *msg);
void must(int r,const char *msg);
void pathdir(const char *path,mode_t mode);
void validate_dir(const char *path);
void mountfs(const char *src,const char *dst,const char *type,unsigned long flags,const char *data);
void bindpath(const char *src,const char *dst,int readonly);
void setup_mounts(const char *root,const char *data,const char *agent,int expose);
void enter_root(const char *root,char **cmd,const char *agent);
void drop_caps(void);
void process_scope(void);
void workload_group_init(const char *app);
void workload_group_join(const char *app);
void workload_group_cleanup(const char *app,int grace);
#endif
