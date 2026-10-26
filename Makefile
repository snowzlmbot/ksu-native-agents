CC ?= gcc
CFLAGS ?= -Os -Wall -Wextra -Werror -D_FORTIFY_SOURCE=2 -fstack-protector-strong
SRC = src/main.c src/mounts.c src/security.c src/lifecycle.c
all: build/ksu-agent
build/ksu-agent: $(SRC) src/agent.h
	mkdir -p build
	$(CC) $(CFLAGS) -static $(SRC) -o $@
	strip $@
check:
	python3 -m compileall -q src
	sh -n module/common/customize.sh module/common/service.sh module/common/uninstall.sh
.PHONY: all check
