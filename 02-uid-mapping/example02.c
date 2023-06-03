#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sched.h>
#include <unistd.h>
#include <sys/types.h>

// Write a single string to the named file.
static void write_str_to(const char *str, const char *path) {
    FILE *f = fopen(path, "w");

    if (!f) {
        fprintf(stderr, "failed to open file %s: %m\n", path);
        exit(EXIT_FAILURE);
    }

    if (fputs(str, f) < 0) {
        fprintf(stderr, "error writing to file %s: %m\n", path);
        exit(EXIT_FAILURE);
    }

    if (fclose(f) < 0) {
        fprintf(stderr, "error closing file %s: %m\n", path);
        exit(EXIT_FAILURE);
    }
}

// Write an id map to the named file. The id map will map 0 in the user
// namespace to the given host_id in the host.
static void write_id_map(const char *path, intmax_t host_id) {
    char mapping[200];
    int written = snprintf(mapping, sizeof(mapping), "0 %jd 1\n", host_id);
    if ((size_t)written > sizeof(mapping) - 1) {
        fputs("tried to write too many chars to file\n", stderr);
        exit(EXIT_FAILURE);
    }

    write_str_to(mapping, path);
}

// Write "deny" to the setgroups file, see user_namespace(7).
static void deny_setgroups() {
    write_str_to("deny", "/proc/self/setgroups");
}

int main(int argc, char *const argv[]) {
    if (argc < 2) {
        fputs("Need at least 1 arg\n", stderr);
        return EXIT_FAILURE;
    }

    uid_t uid = geteuid();
    gid_t gid = getegid();

    if (unshare(CLONE_NEWUSER) < 0) {
        perror("error from unshare");
        return EXIT_FAILURE;
    }

    // We have to disable setgroups in order to write a gid_map.
    deny_setgroups();
    write_id_map("/proc/self/uid_map", (intmax_t)uid);
    write_id_map("/proc/self/gid_map", (intmax_t)gid);

    if (execvp(argv[1], &argv[1]) < 0) {
        perror("error from execvp");
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
