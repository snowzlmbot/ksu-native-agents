#include "agent.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <signal.h>
#include <dirent.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/prctl.h>
#include <limits.h>
#include <time.h>
#include <stdint.h>

#ifndef SYS_pidfd_open
#define SYS_pidfd_open 434
#endif
#ifndef SYS_pidfd_send_signal
#define SYS_pidfd_send_signal 424
#endif

static const char *app;
static char state[PATH_MAX], root[PATH_MAX], run[PATH_MAX];
static volatile sig_atomic_t ending = 0;

static void onterm(int sig) { (void)sig; ending = 1; }
static void die_msg(const char *msg) { perror(msg); exit(1); }

static int read_file_limited(const char *path, char *buf, size_t cap) {
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return -1;
    ssize_t n = read(fd, buf, cap - 1);
    int saved = errno;
    close(fd);
    errno = saved;
    if (n < 0) return -1;
    buf[n] = 0;
    return (int)n;
}

static int boot_id(char *out, size_t cap) {
    int n = read_file_limited("/proc/sys/kernel/random/boot_id", out, cap);
    if (n < 0) return -1;
    char *nl = strchr(out, '\n'); if (nl) *nl = 0;
    return *out ? 0 : -1;
}

static int proc_start_ticks(pid_t pid, unsigned long long *out) {
    char path[64], raw[4096];
    snprintf(path, sizeof path, "/proc/%d/stat", pid);
    if (read_file_limited(path, raw, sizeof raw) < 0) return -1;
    char *end = strrchr(raw, ')');
    if (!end) return -1;
    char *save = NULL, *tok = strtok_r(end + 1, " \t\r\n", &save);
    unsigned long long value = 0;
    for (int i = 0; tok; i++, tok = strtok_r(NULL, " \t\r\n", &save)) {
        if (i == 19) {
            char *stop = NULL;
            errno = 0; value = strtoull(tok, &stop, 10);
            if (errno || !stop || *stop) return -1;
            *out = value; return 0;
        }
    }
    return -1;
}

static int pidfd_for(pid_t pid) {
    return (int)syscall(SYS_pidfd_open, pid, 0);
}

static int send_pidfd(int fd, int sig) {
    return (int)syscall(SYS_pidfd_send_signal, fd, sig, NULL, 0);
}

static void safe_unlink(const char *path) {
    struct stat st;
    if (lstat(path, &st) == 0) (void)unlink(path);
}

static int write_pid_record(void) {
    char p[PATH_MAX], tmp[PATH_MAX], bid[128];
    unsigned long long ticks;
    if (proc_start_ticks(getpid(), &ticks) < 0 || boot_id(bid, sizeof bid) < 0) {
        errno = EIO; return -1;
    }
    snprintf(p, sizeof p, "%s/pid", run);
    int n = snprintf(tmp, sizeof tmp, "%s/.pid.%d", run, (int)getpid());
    if (n < 0 || (size_t)n >= sizeof tmp) { errno = ENAMETOOLONG; return -1; }
    int fd = open(tmp, O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0) return -1;
    char text[512];
    n = snprintf(text, sizeof text, "pid=%d\nticks=%llu\nboot=%s\napp=%s\n",
                 (int)getpid(), ticks, bid, app);
    int ok = (n > 0 && (size_t)n < sizeof text && write(fd, text, (size_t)n) == n);
    if (ok) ok = fsync(fd) == 0;
    int saved = errno;
    close(fd);
    errno = saved;
    if (!ok) { safe_unlink(tmp); return -1; }
    if (rename(tmp, p) < 0) { safe_unlink(tmp); return -1; }
    return 0;
}

struct pid_record { pid_t pid; unsigned long long ticks; char boot[128]; char name[32]; };

static int read_pid_record(struct pid_record *r) {
    memset(r, 0, sizeof *r);
    char p[PATH_MAX], text[1024];
    snprintf(p, sizeof p, "%s/pid", run);
    int fd = open(p, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return -1;
    struct stat st;
    if (fstat(fd, &st) < 0 || !S_ISREG(st.st_mode) || st.st_nlink != 1 || st.st_uid != 0) {
        close(fd); errno = EPERM; return -1;
    }
    ssize_t n = read(fd, text, sizeof text - 1); close(fd);
    if (n <= 0) { errno = EINVAL; return -1; }
    text[n] = 0;
    char *save = NULL;
    for (char *line = strtok_r(text, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        if (!strncmp(line, "pid=", 4)) r->pid = (pid_t)strtol(line + 4, NULL, 10);
        else if (!strncmp(line, "ticks=", 6)) r->ticks = strtoull(line + 6, NULL, 10);
        else if (!strncmp(line, "boot=", 5)) snprintf(r->boot, sizeof r->boot, "%s", line + 5);
        else if (!strncmp(line, "app=", 4)) snprintf(r->name, sizeof r->name, "%s", line + 4);
    }
    if (r->pid <= 0 || !r->ticks || !r->boot[0] || strcmp(r->name, app)) { errno = EINVAL; return -1; }
    return 0;
}

static int cmdline_is_ours(pid_t pid) {
    char p[64], raw[2048];
    snprintf(p, sizeof p, "/proc/%d/cmdline", pid);
    int n = read_file_limited(p, raw, sizeof raw);
    if (n < 0) return 0;
    for (int i = 0; i < n; i++) if (!raw[i]) raw[i] = ' ';
    return strstr(raw, "ksu-agent") && strstr(raw, app) && strstr(raw, "supervise");
}

static int record_matches_live(const struct pid_record *r, int *pidfd_out) {
    char bid[128]; unsigned long long ticks;
    if (boot_id(bid, sizeof bid) < 0 || strcmp(bid, r->boot)) return 0;
    if (proc_start_ticks(r->pid, &ticks) < 0 || ticks != r->ticks) return 0;
    if (!cmdline_is_ours(r->pid)) return 0;
    int pfd = pidfd_for(r->pid);
    if (pfd < 0) return 0;
    if (pidfd_out) *pidfd_out = pfd; else close(pfd);
    return 1;
}

static int lock_run(void) {
    pathdir(state, 0700);
    snprintf(run, sizeof run, "%s/run", state);
    pathdir(run, 0700);
    char p[PATH_MAX]; snprintf(p, sizeof p, "%s/lock", run);
    int fd = open(p, O_CREAT | O_RDWR | O_NOFOLLOW | O_CLOEXEC, 0600);
    must(fd, "open lock");
    struct stat st; must(fstat(fd, &st), "stat lock");
    if (!S_ISREG(st.st_mode) || st.st_nlink != 1 || st.st_uid != 0) { errno = EPERM; die_msg("lock type"); }
    struct flock l = { .l_type = F_WRLCK, .l_whence = SEEK_SET };
    if (fcntl(fd, F_SETLK, &l) < 0) { puts("already running"); exit(0); }
    return fd;
}

static int wait_child_bounded(pid_t child, int *status, int seconds) {
    const long step_ns = 100000000L;
    for (int i = 0; i < seconds * 10; i++) {
        pid_t w = waitpid(child, status, WNOHANG);
        if (w == child) return 1;
        if (w < 0 && errno == ECHILD) return 1;
        struct timespec ts = { 0, step_ns }; nanosleep(&ts, NULL);
    }
    return 0;
}

static int run_command(char **cmd, int expose);

static int supervise(void) {
    int lock = lock_run();
    workload_group_init(app);
    signal(SIGPIPE, SIG_IGN);
    struct sigaction sa; memset(&sa, 0, sizeof sa); sa.sa_handler = onterm; sigemptyset(&sa.sa_mask);
    if (sigaction(SIGTERM, &sa, NULL) < 0 || sigaction(SIGINT, &sa, NULL) < 0) die_msg("sigaction");
    signal(SIGHUP, SIG_IGN);
    if (write_pid_record() < 0) die_msg("write pid record");
    char p[PATH_MAX]; snprintf(p, sizeof p, "%s/supervisor.log", run);
    int logfd = open(p, O_CREAT | O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC, 0600);
    must(logfd, "open log");
    struct stat lst; must(fstat(logfd, &lst), "stat log");
    if (!S_ISREG(lst.st_mode) || lst.st_nlink != 1 || lst.st_uid != 0) { errno = EPERM; die_msg("log type"); }
    must(dup2(logfd, STDOUT_FILENO), "redirect stdout");
    must(dup2(logfd, STDERR_FILENO), "redirect stderr");
    close(logfd);
    dprintf(STDOUT_FILENO, "supervisor %s pid=%d\n", app, (int)getpid());
    (void)lock;
    int tries = 0, status = 0;
    while (!ending && tries++ < 4) {
        char noauto[PATH_MAX]; snprintf(noauto, sizeof noauto, "%s/NO_AUTOSTART", state);
        if (access(noauto, F_OK) == 0) break;
        pid_t child = fork();
        must(child, "fork");
        if (child == 0) {
            (void)prctl(PR_SET_PDEATHSIG, SIGTERM);
            if (getppid() == 1) _exit(125);
            if (setsid() < 0) _exit(126);
            workload_group_join(app);
            char *child_cmd[] = { "/bin/bash", "/opt/ksu-agent/start.sh", NULL };
            run_command(child_cmd, 1);
            _exit(1);
        }
        for (;;) {
            pid_t w = waitpid(child, &status, 0);
            if (w == child) break;
            if (w < 0 && errno != EINTR) break;
            if (ending) break;
        }
        if (ending) {
            workload_group_cleanup(app, 15);
            (void)wait_child_bounded(child, &status, 5);
            break;
        }
        // Includes descendants that changed session or process group.
        workload_group_cleanup(app, 5);
        dprintf(STDERR_FILENO, "service exited status=%d attempt=%d/4\n", status, tries);
        if (tries < 4) { struct timespec ts = { tries * 10, 0 }; nanosleep(&ts, NULL); }
    }
    char pidpath[PATH_MAX]; snprintf(pidpath, sizeof pidpath, "%s/pid", run);
    safe_unlink(pidpath);
    return 0;
}

static int run_command(char **cmd, int expose) {
    if (unshare(CLONE_NEWNS) < 0) die_msg("private mount namespace");
    process_scope();
    setup_mounts(root, state, app, expose);
    enter_root(root, cmd, app);
    return 1;
}

int main(int argc, char **argv) {
    if (getuid() != 0) { errno = EPERM; die_msg("KernelSU root required"); }
    if (argc < 3) { fprintf(stderr, "usage: ksu-agent openclaw|hermes supervise|stop|status|exec CMD...\n"); return 2; }
    app = argv[1];
    if (strcmp(app, "openclaw") && strcmp(app, "hermes")) { errno = EINVAL; die_msg("agent name"); }
    snprintf(state, sizeof state, "%s/%s", BASE, app);
    if (lstat(BASE, &(struct stat){0}) < 0 || lstat(state, &(struct stat){0}) < 0) {
        if (!strcmp(argv[2], "status") || !strcmp(argv[2], "stop")) return 0;
        die_msg("agent data directory");
    }
    validate_dir(BASE); validate_dir(state);
    const char *op = argv[2];
    if (!strcmp(op, "status") || !strcmp(op, "stop")) {
        snprintf(run, sizeof run, "%s/run", state);
        if (lstat(run, &(struct stat){0}) < 0) {
            if (!strcmp(op, "status")) printf("%s stopped pid=0 rootfs=unresolved\n", app);
            return 0;
        }
        validate_dir(run);
        struct pid_record rec;
        int pfd = -1, live = read_pid_record(&rec) == 0 && record_matches_live(&rec, &pfd);
        if (!strcmp(op, "status")) {
            char cur[PATH_MAX], resolved[PATH_MAX] = "unresolved";
            snprintf(cur, sizeof cur, "%s/current", state);
            if (!realpath(cur, resolved)) snprintf(resolved, sizeof resolved, "unresolved");
            printf("%s %s pid=%d rootfs=%s\n", app, live ? "running" : "stopped", live ? rec.pid : 0, resolved);
            if (pfd >= 0) close(pfd);
            return 0;
        }
        if (live) {
            if (send_pidfd(pfd, SIGTERM) < 0 && errno == ENOSYS) (void)kill(rec.pid, SIGTERM);
            close(pfd);
        }
        return 0;
    }
    char cur[PATH_MAX]; snprintf(cur, sizeof cur, "%s/current", state);
    if (!realpath(cur, root)) die_msg("current rootfs");
    char prefix[PATH_MAX]; snprintf(prefix, sizeof prefix, "%s/versions/", state);
    size_t plen = strlen(prefix);
    if (strncmp(root, prefix, plen) || !root[plen] || strchr(root + plen, '/')) { errno = EPERM; die_msg("rootfs outside fixed version directory"); }
    validate_dir(root);
    if (!strcmp(op, "supervise")) return supervise();
    if (!strcmp(op, "exec") && argc > 3) return run_command(argv + 3, 1);
    fprintf(stderr, "unknown operation\n"); return 2;
}
