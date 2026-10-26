#define _GNU_SOURCE
#include <unistd.h>
#include <sys/syscall.h>
#include <errno.h>
#include <stdio.h>
#include <sched.h>
#include <sys/stat.h>
int main(void) {
 errno=0; long abi=syscall(444, NULL, 0, 1);
 printf("landlock_abi=%ld errno=%d\n",abi,errno);
 const char *p[] = {"/sys/fs/cgroup/cgroup.kill", "/sys/fs/cgroup/cgroup.controllers",NULL};
 for(int i=0;p[i];i++) { struct stat s; errno=0; int r=stat(p[i],&s); printf("%s present=%d errno=%d\n",p[i],r==0,errno); }
 return 0;
}
