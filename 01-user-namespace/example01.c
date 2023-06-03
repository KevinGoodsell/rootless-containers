#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sched.h>
#include <unistd.h>
#include <sys/capability.h>

static void print_caps(void) {
    cap_t caps = cap_get_proc();
    if (!caps) {
        perror("error from cap_get_proc");
        exit(EXIT_FAILURE);
    }
    char *caps_text = cap_to_text(caps, NULL);
    if (!caps_text) {
        perror("error from cap_to_text");
        exit(EXIT_FAILURE);
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
        return EXIT_FAILURE;
    }

    if (argc < 2) {
        print_caps();
        return EXIT_SUCCESS;
    }

    if (execvp(argv[1], &argv[1]) < 0) {
        perror("error from execvp");
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
