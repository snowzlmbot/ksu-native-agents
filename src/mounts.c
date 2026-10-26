#include "agent.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <limits.h>
#include <ctype.h>
void die(const char *msg){perror(msg);exit(1);}
void must(int r,const char *msg){if(r<0)die(msg);}
void validate_dir(const char *path){
 char b[PATH_MAX];struct stat s;
 if(strlen(path)>=sizeof b||path[0]!='/'){errno=EINVAL;die("absolute directory required");}
 strcpy(b,path);
 for(char *p=b+1;;p++)if(*p=='/'||!*p){char c=*p;*p=0;
  must(lstat(b,&s),b);if(!S_ISDIR(s.st_mode)){errno=ENOTDIR;die(b);}*p=c;if(!c)break;}
}
void pathdir(const char *path,mode_t mode){
 if(mkdir(path,mode)<0&&errno!=EEXIST)die(path);
 validate_dir(path);
}
void mountfs(const char *src,const char *dst,const char *type,unsigned long flags,const char *data){
 must(mount(src,dst,type,flags,data),dst);
}
void bindpath(const char *src,const char *dst,int readonly){
 validate_dir(src);validate_dir(dst);
 mountfs(src,dst,NULL,MS_BIND,NULL);
 if(readonly)mountfs(NULL,dst,NULL,MS_BIND|MS_REMOUNT|MS_RDONLY|MS_NOSUID|MS_NODEV,NULL);
}
static void pdir(const char *r,const char *p){char b[PATH_MAX];snprintf(b,sizeof b,"%s/%s",r,p);pathdir(b,0755);}
static void tmpfs(const char *r,const char *p,const char *opts){char b[PATH_MAX];snprintf(b,sizeof b,"%s/%s",r,p);mountfs("tmpfs",b,"tmpfs",MS_NOSUID|MS_NODEV,opts);}
static void device(const char *r,const char *name){
 char s[128],d[PATH_MAX];snprintf(s,sizeof s,"/dev/%s",name);snprintf(d,sizeof d,"%s/dev/%s",r,name);
 FILE *f=fopen(d,"w");if(!f)die(d);fclose(f);mountfs(s,d,NULL,MS_BIND,NULL);
}
static void extra_mounts(const char *r,const char *state){
 char config[PATH_MAX],line[PATH_MAX+128];
 snprintf(config,sizeof config,"%s/mounts.tsv",state);
 FILE *f=fopen(config,"re");if(!f){if(errno==ENOENT)return;die("mounts.tsv");}
 struct stat st;must(fstat(fileno(f),&st),"mount config stat");
 if(!S_ISREG(st.st_mode)||st.st_uid!=0||st.st_nlink!=1){errno=EPERM;die("mount config type");}
 while(fgets(line,sizeof line,f)){
  if(line[0]=='#'||line[0]=='\n')continue;
  char *nl=strchr(line,'\n');if(nl)*nl=0;
  char *source=strchr(line,'\t');if(!source){errno=EINVAL;die("mounts.tsv needs label TAB absolute-path");}
  *source++=0;if(!*line||strlen(line)>48||!*source){errno=EINVAL;die("invalid map");}
  for(char *c=line;*c;c++)if(!isalnum((unsigned char)*c)&&*c!='_'&&*c!='-'){errno=EINVAL;die("invalid map label");}
  char resolved[PATH_MAX],target[PATH_MAX];if(!realpath(source,resolved))die("map source");
  if(!strcmp(resolved,"/")||!strncmp(resolved,"/proc",5)||!strncmp(resolved,"/sys",4)||!strncmp(resolved,"/dev",4)){
   errno=EPERM;die("kernel control trees cannot be mapped");
  }
  int n=snprintf(target,sizeof target,"%s/host/%s",r,line);if(n<0||(size_t)n>=sizeof target){errno=ENAMETOOLONG;die("map target");}
  struct stat t;if(lstat(target,&t)==0){errno=EEXIST;die("reserved/duplicate map label");}
  pathdir(target,0755);bindpath(resolved,target,0);
  if(!strncmp(resolved,"/data/adb",9))fprintf(stderr,"WARNING: sensitive RW mapping /host/%s grants KernelSU control-data access\n",line);
 }
 if(ferror(f))die("read mount config");
 fclose(f);
}
void setup_mounts(const char *r,const char *state,const char *agent,int expose){
 (void)agent;char s[PATH_MAX],d[PATH_MAX];
 validate_dir(r);validate_dir(state);
 mountfs(NULL,"/",NULL,MS_REC|MS_PRIVATE,NULL);
 mountfs(r,r,NULL,MS_BIND,NULL);
 const char *dirs[]={"dev","proc","sys","run","tmp","host","root","workspace",NULL};
 for(int i=0;dirs[i];i++)pdir(r,dirs[i]);
 tmpfs(r,"dev","mode=0755,size=8m");
 const char *devices[]={"null","zero","random","urandom","tty",NULL};
 for(int i=0;devices[i];i++)device(r,devices[i]);
 pdir(r,"dev/pts");pdir(r,"dev/shm");
 snprintf(d,sizeof d,"%s/dev/pts",r);
 mountfs("devpts",d,"devpts",MS_NOSUID|MS_NOEXEC,"newinstance,ptmxmode=0666,mode=0620,gid=5");
 snprintf(d,sizeof d,"%s/dev/ptmx",r);must(symlink("pts/ptmx",d),"ptmx symlink");
 snprintf(d,sizeof d,"%s/dev/fd",r);must(symlink("/proc/self/fd",d),"fd symlink");
 tmpfs(r,"dev/shm","mode=1777,size=256m");
 tmpfs(r,"run","mode=0755,size=32m");tmpfs(r,"tmp","mode=1777,size=512m");
 tmpfs(r,"sys","mode=0555,size=1m");
 snprintf(d,sizeof d,"%s/proc",r);mountfs("proc",d,"proc",MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL);
 snprintf(s,sizeof s,"%s/home",state);snprintf(d,sizeof d,"%s/root",r);bindpath(s,d,0);
 snprintf(s,sizeof s,"%s/workspace",state);snprintf(d,sizeof d,"%s/workspace",r);bindpath(s,d,0);
 tmpfs(r,"host","mode=0755,size=4m");
 if(expose){
  const char *sources[]={"/data","/storage/emulated/0","/system","/vendor","/product","/system_ext","/odm",NULL};
  const char *names[]={"data","storage","system","vendor","product","system_ext","odm"};
  for(int i=0;sources[i];i++){
   if(access(sources[i],F_OK))continue;
   snprintf(d,sizeof d,"%s/host/%s",r,names[i]);pathdir(d,0755);bindpath(sources[i],d,0);
  }
  /* Never recursively enumerate/chmod/unmount a host bind. Hide own storage. */
  snprintf(d,sizeof d,"%s/host/data/adb",r);
  struct stat st;must(lstat(d,&st),"required adb mask target");
  if(!S_ISDIR(st.st_mode)){errno=ENOTDIR;die("adb mask target");}
  mountfs("tmpfs",d,"tmpfs",MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC,"mode=000,size=4k");
  extra_mounts(r,state);
 }
}
