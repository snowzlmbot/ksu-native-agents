#include "agent.h"
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>

#define CG_BASE "/sys/fs/cgroup/ksu_native_agents"
static int cg_open(const char *app,const char *file,int flags){
 char p[256];int n=snprintf(p,sizeof p,"%s/%s/%s",CG_BASE,app,file);
 if(n<0||(size_t)n>=sizeof p){errno=ENAMETOOLONG;return -1;}
 return open(p,flags|O_CLOEXEC|O_NOFOLLOW);
}
static int write_control(int fd,const char *value){
 size_t n=strlen(value);ssize_t w=write(fd,value,n);int e=errno;close(fd);errno=e;
 return w==(ssize_t)n?0:-1;
}
void workload_group_init(const char *app){
 pathdir(CG_BASE,0700);char p[256];snprintf(p,sizeof p,"%s/%s",CG_BASE,app);pathdir(p,0700);
 int fd=cg_open(app,"cgroup.kill",O_WRONLY);must(fd,"cgroup.kill required");close(fd);
 int q=cg_open(app,"cgroup.procs",O_RDONLY);must(q,"cgroup.procs");char b[32];ssize_t n=read(q,b,sizeof b);close(q);
 if(n!=0){errno=EBUSY;die("previous workload still in own cgroup; refuse duplicate");}
}
void workload_group_join(const char *app){
 int fd=cg_open(app,"cgroup.procs",O_WRONLY);must(fd,"join own cgroup");
 must(write_control(fd,"0"),"move self into own cgroup");
}
static void group_term(const char *app){
 int fd=cg_open(app,"cgroup.procs",O_RDONLY);if(fd<0)die("read own cgroup");
 FILE *f=fdopen(fd,"r");if(!f)die("cgroup stream");long pid;
 while(fscanf(f,"%ld",&pid)==1){
  if(pid<=1||pid==getpid())continue;
  int pf=(int)syscall(SYS_pidfd_open,pid,0);if(pf<0)continue;
  /* Membership recheck after pinning the task prevents PID reuse races. */
  int check=cg_open(app,"cgroup.procs",O_RDONLY);FILE *in=check<0?NULL:fdopen(check,"r");int member=0;long p;
  if(in){while(fscanf(in,"%ld",&p)==1)if(p==pid)member=1;fclose(in);}
  if(member)(void)syscall(SYS_pidfd_send_signal,pf,SIGTERM,NULL,0);
  close(pf);
 }
 fclose(f);
}
static int group_empty(const char *app){
 int fd=cg_open(app,"cgroup.events",O_RDONLY);if(fd<0)return 0;
 char b[1024];ssize_t n=read(fd,b,sizeof b-1);close(fd);if(n<0)return 0;b[n]=0;
 return strstr(b,"populated 0")!=NULL;
}
void workload_group_cleanup(const char *app,int grace){
 group_term(app);
 for(int i=0;i<grace*10;i++){
  if(group_empty(app))return;
  struct timespec ts={0,100000000};nanosleep(&ts,NULL);
 }
 int fd=cg_open(app,"cgroup.kill",O_WRONLY);must(fd,"own cgroup force-stop");
 must(write_control(fd,"1"),"own cgroup kill");
 for(int i=0;i<50;i++){
  if(group_empty(app))return;
  struct timespec ts={0,100000000};nanosleep(&ts,NULL);
 }
 errno=EBUSY;die("own cgroup not empty; preserving all data");
}
