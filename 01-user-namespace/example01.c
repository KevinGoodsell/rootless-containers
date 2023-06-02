#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sched.h>
#include <unistd.h>
#include <sys/capability.h>

void print_caps(void) {
    cap_t caps = cap_get_proc();
    if (!caps) {
        perror("error from cap_get_proc");
        exit(1);
    }
    char *caps_text = cap_to_text(caps, NULL);
    if (!caps_text) {
        perror("error from cap_to_text");
        exit(1);
    }
    printf("Capabilities: %s\n", caps_text);
    cap_free(caps_text);
    cap_free(caps);
}

int main(int argc, char *const argv[]) {

    // unshare(2) moves the process to a new namespace, so it no longer shares
    // its namespace with other processes.
    if (unshare(CLONE_NEWUSER) < 0) {
        perror("error from unshare");
        return 1;
    }

    if (argc < 2) {
        print_caps();
        return 0;
    }

    if (execvp(argv[1], &argv[1]) < 0) {
        perror("error from execvp");
        return 1;
    }

    return 0;
}

