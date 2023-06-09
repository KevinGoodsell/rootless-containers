#define _GNU_SOURCE
#include <getopt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sched.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

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

static void usage(const char *progname) {
    printf("Run a command in a new namespace\n");
    printf("\n");
    printf("Usage:\n");
    printf("\n");
    printf("  %s [opts] -- CMD [CMD_ARGS...]\n", progname);
    printf("\n");
    printf("Opts:\n");
    printf("\n");
    printf("  -h, --help          Print this help and exit\n");
    printf("  --hosname HOSTNAME  Set hostame in the new namespace\n");
}

// Argument values for long-only options, chosen to not conflict with ASCII
// characters.
enum long_arg_index {
    HOSTNAME_ARG = 200
};

int main(int argc, char *const argv[]) {

    static struct option long_options[] = {
        {"hostname", required_argument, 0, HOSTNAME_ARG},
        {"help",     no_argument,       0, 'h'},
        {0,          0,                 0, 0}
    };

    int c;
    const char *hostname = NULL;

    while (1) {
        c = getopt_long(argc, argv, "h", long_options, NULL);

        if (c == -1) {
            break;
        }

        switch (c) {
        case 'h':
            usage(argv[0]);
            return EXIT_SUCCESS;

        case HOSTNAME_ARG:
            hostname = optarg;
            break;

        case '?':
            // Seems like getopt has already reported the error by the time we
            // get here.
            return EXIT_FAILURE;

        default:
            fprintf(stderr, "getopt returned character code %c\n", c);
            return EXIT_FAILURE;
        }
    }

    int arg_count = argc - optind;
    char *const *args_start = argv + optind;

    if (arg_count < 1) {
        fputs("Need at least 1 arg\n", stderr);
        return EXIT_FAILURE;
    }

    uid_t uid = geteuid();
    gid_t gid = getegid();

    if (unshare(CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWUTS) < 0) {
        perror("error from unshare");
        return EXIT_FAILURE;
    }

    // We have to disable setgroups in order to write a gid_map.
    deny_setgroups();
    write_id_map("/proc/self/uid_map", (intmax_t)uid);
    write_id_map("/proc/self/gid_map", (intmax_t)gid);

    // We need a new process in the PID namespace to be PID 1, which will run
    // until we're done with the namespaces. PID 1 exiting would be bad.

    pid_t child_pid = fork();

    if (child_pid < 0) {
        perror("error from fork");
        return EXIT_FAILURE;
    }

    if (child_pid == 0) {
        // Child process

        // Set the hostname
        if (hostname) {
            if (sethostname(hostname, strlen(hostname)) < 0) {
                perror("error from sethostname");
                return EXIT_FAILURE;
            }
        }

        // Run the command
        if (execvp(args_start[0], args_start) < 0) {
            perror("error from execvp");
            return EXIT_FAILURE;
        }
    }

    // Parent process, wait for child
    pid_t exited_pid = waitpid(child_pid, NULL, 0);

    if (exited_pid < 0) {
        perror("error from waitpid");
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
