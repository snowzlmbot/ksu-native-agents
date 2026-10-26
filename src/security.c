#include "agent.h"
#include <linux/capability.h>
#include <linux/securebits.h>
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <stddef.h>
#include <errno.h>
#include <stdint.h>
void process_scope(void){
 struct { uint64_t fs, net, scoped; } rules={0,0,3};
 long abi=syscall(444,NULL,0,1);
 if(abi<6){errno=ENOTSUP;die("Landlock ABI 6 required; no unsafe fallback");}
 int fd=(int)syscall(444,&rules,sizeof rules,0);
 must(fd,"Landlock scope ruleset");
 must(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0),"scope no new privileges");
 int result=(int)syscall(446,fd,0);int error=errno;close(fd);errno=error;
 must(result,"Landlock signal/abstract Unix scope");
}
#define DENY(n) BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,__NR_##n,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM)
void drop_caps(void){
 unsigned keep=(1u<<CAP_CHOWN)|(1u<<CAP_DAC_OVERRIDE)|
 (1u<<CAP_FOWNER)|(1u<<CAP_FSETID)|(1u<<CAP_NET_BIND_SERVICE);
 must(prctl(PR_SET_SECUREBITS,SECBIT_NOROOT|SECBIT_NOROOT_LOCKED|SECBIT_NO_SETUID_FIXUP|SECBIT_NO_SETUID_FIXUP_LOCKED),"securebits");
 for(int n=0;n<=40;n++)if(n>=32||!(keep&(1u<<n)))
  if(prctl(PR_CAPBSET_DROP,n,0,0,0)<0&&errno!=EINVAL)die("cap bounding");
 struct __user_cap_header_struct h={_LINUX_CAPABILITY_VERSION_3,0};
 struct __user_cap_data_struct c[2]={{keep,keep,keep},{0,0,0}};
 must(syscall(SYS_capset,&h,c),"capset");
 for(int n=0;n<32;n++)if(keep&(1u<<n))must(prctl(PR_CAP_AMBIENT,PR_CAP_AMBIENT_RAISE,n,0,0),"ambient cap");
 must(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0),"no new privileges");
 struct sock_filter f[]={
 BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,arch)),
 BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AUDIT_ARCH_AARCH64,1,0),
 BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
 BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
 DENY(mount),DENY(umount2),DENY(pivot_root),DENY(chroot),DENY(setns),DENY(unshare),
 DENY(reboot),DENY(kexec_load),DENY(init_module),DENY(finit_module),DENY(delete_module),
 DENY(ptrace),DENY(process_vm_writev),DENY(process_vm_readv),DENY(pidfd_getfd),
 DENY(bpf),DENY(open_by_handle_at),DENY(swapon),DENY(swapoff),
 DENY(fsopen),DENY(fsconfig),DENY(fsmount),DENY(open_tree),DENY(move_mount),DENY(fspick),DENY(mount_setattr),
 BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW)};
 struct sock_fprog p={sizeof(f)/sizeof(f[0]),f};
 must(prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&p),"seccomp");
}
void enter_root(const char *r,char **cmd,const char *agent){
 must(chdir(r),"cd rootfs");must(chroot("."),"chroot");must(chdir("/workspace"),"cd workspace");
 clearenv();setenv("HOME","/root",1);setenv("USER","root",1);setenv("LOGNAME","root",1);
 setenv("PATH","/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",1);
 setenv("LANG","C.UTF-8",1);setenv("TERM","xterm-256color",1);setenv("TZ","Asia/Shanghai",1);
 setenv("HERMES_HOME","/root/.hermes",1);setenv("HERMES_TERMINAL_BACKEND","local",1);
 setenv("KSU_AGENT",agent,1);setenv("NODE_OPTIONS","--max-old-space-size=1024",1);
 setenv("TMPDIR","/tmp",1);setenv("NPM_CONFIG_PREFIX","/usr/local",1);
 setenv("SHELL","/bin/bash",1);setenv("OPENCLAW_SUPERVISOR_MODE","external",1);
 setenv("OPENCLAW_SERVICE_REPAIR_POLICY","external",1);
 if(syscall(SYS_close_range,3u,~0u,0)<0){
  for(int fd=3;fd<65536;fd++)close(fd);
 }
 struct rlimit rl={8192,8192};must(setrlimit(RLIMIT_NOFILE,&rl),"nofile");
 setpriority(PRIO_PROCESS,0,10);umask(0077);drop_caps();
 execvp(cmd[0],cmd);die("exec container command");
}
