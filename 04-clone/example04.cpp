#include <array>
#include <csignal>
#include <cstdlib>
#include <fcntl.h>
#include <getopt.h>
#include <iostream>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

using std::cout;
using std::endl;
using std::string;

// XXX Maybe I should stick with C++17. For g++ c++20 is experimental. I only
// switched to get std::span, and could just use gsl::span.

// XXX Document, maybe group with other class
class event {
    public:
        event() {
            std::array<int, 2> pipe{};
            if (pipe2(pipe.data(), O_CLOEXEC) < 0) {
                perror("error from pipe2");
                throw std::runtime_error("pipe2 failed");
            }

            this->read_pipe = pipe[0];
            this->write_pipe = pipe[1];
        }

        event(const event &) = delete;
        event(const event &&) = delete;
        auto operator= (const event &) -> event& = delete;
        auto operator= (const event &&) -> event&& = delete;

        ~event() {
            try {
                close();
            } catch (...) {
                // Errors are already printed, not much else we can do.
            }
        }

        // Block until set() is called
        void wait() {
            close_write();

            char buf = 0;
            auto read_bytes = read(this->read_pipe, &buf, 1);
            if (read_bytes < 0) {
                perror("error reading from pipe in wait");
                throw std::runtime_error("failed to read pipe in wait");
            }

            close_read();
        }

        // Release callers of wait()
        void set() {
            close();
        }

        // Close all fds, calling wait() or set() after this is undefined.
        void close() {
            close_write();
            close_read();
        }

    private:
        void close_read() {
            if (this->read_pipe < 0) {
                return;
            }

            if (::close(this->read_pipe) < 0) {
                perror("error closing read end of pipe");
                throw std::runtime_error("failed to close read end of pipe");
            }
            this->read_pipe = -1;
        }

        void close_write() {
            if (this->write_pipe < 0) {
                return;
            }

            if (::close(this->write_pipe) < 0) {
                perror("error closing write end of pipe");
                throw std::runtime_error("failed to close write end of pipe");
            }
            this->write_pipe = -1;
        }

        int read_pipe;
        int write_pipe;
};

// XXX Should just change this to stop on the first non-opt argument. Too
// awkward to use -- all the time, or get unexpected results.
static void usage(const string& progname) {
    cout << "Run a command in a new namespace\n";
    cout << "\n";
    cout << "Usage:\n";
    cout << "\n";
    cout << "  " << progname << " [opts] -- CMD [CMD_ARGS...]\n";
    cout << "\n";
    cout << "Opts:\n";
    cout << "\n";
    cout << "  -h, --help          Print this help and exit\n";
    cout << "  --hosname HOSTNAME  Set hostame in the new namespace" << endl;
}

// Argument values for long-only options, chosen to not conflict with ASCII
// characters.
enum long_arg_index {
    HOSTNAME_ARG = 200
};

// Manage allocation and deallocation of a stack for use with clone(2).
class clone_stack {
    public:
        explicit clone_stack(size_t size) : size(size) {
            void* vp_stack = mmap(
                nullptr, // anywhere
                size,
                PROT_READ | PROT_WRITE,
                MAP_PRIVATE | MAP_ANONYMOUS | MAP_STACK,
                -1,  // No file, some implementations require -1 for anon
                0);  // offset should be 0 for anon

            if (vp_stack == MAP_FAILED) {
                perror("error from mmap");
                throw std::runtime_error("mmap failed");
            }

            this->stack = static_cast<char*>(vp_stack);
        }

        ~clone_stack() {
            if (munmap(this->stack, this->size) < 0) {
                perror("error from munmap");
            }
        }

        clone_stack(const clone_stack&) = delete;
        clone_stack(const clone_stack&&) = delete;
        auto operator= (const clone_stack&) -> clone_stack& = delete;
        auto operator= (const clone_stack&&) -> clone_stack& = delete;

        [[nodiscard]] auto top() const noexcept -> char* {
            return this->stack + this->size; // NOLINT(cppcoreguidelines-pro-bounds-pointer-arithmetic)
        }

    private:
        size_t size;
        char* stack;
};

// XXX Originally this was a struct, just a data bag for passing to the child.
// This has been a problem for clang tidy, pointers, public members,
// uninitialized members. Is there a "modern" version? Does it have to be a
// full-blown class with accessors?
struct child_args {
    event& evnt;
    const string hostname;
    const std::span<char* const> cmd_line;

    child_args(event& evnt, string hostname, const std::span<char* const> cmd_line)
        : evnt(evnt), hostname(std::move(hostname)), cmd_line(cmd_line)
    {}
};

auto child_fn(void *arg) -> int {
    // XXX Should this be 'auto args = ...'?
    auto *args = static_cast<child_args *>(arg);

    // Wait for parent to signal us before continuing. This lets the parent set
    // up uid_map and gid_map before we do anything that might need the
    // mappings.
    args->evnt.wait();

    // Set the hostname
    if (!args->hostname.empty()) {
        if (sethostname(args->hostname.c_str(), args->hostname.size()) < 0) {
            perror("error from sethostname");
            return EXIT_FAILURE;
        }
    }

    // Run the command
    if (execvp(args->cmd_line[0], args->cmd_line.data()) < 0) {
        perror("error from execvp");
        return EXIT_FAILURE;
    }

    // Not reachable.
    return EXIT_SUCCESS;
}

auto main(int argc, char *const argv[]) -> int {

    // XXX How can we deduce the size of a std::array?
    std::array long_options{
        option{"hostname", required_argument, nullptr, HOSTNAME_ARG},
        option{"help",     no_argument,       nullptr, 'h'},
        option{0,          0,                 nullptr, 0}
    };

    int c;
    string hostname;

    while (true) {
        c = getopt_long(argc, argv, "h", long_options.data(), nullptr);

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
            std::cerr << "getopt returned character code " << c << endl;
            return EXIT_FAILURE;
        }
    }

    int arg_count = argc - optind;
    char *const *args_start = argv + optind;

    if (arg_count < 1) {
        std::cerr << "Need at least 1 arg" << endl;
        return EXIT_FAILURE;
    }

    event evnt;
    child_args cargs(evnt, hostname, std::span(args_start, arg_count + 1));
    //cargs.evnt = &evnt;
    //cargs.hostname = hostname;
    //cargs.cmd_line = args_start;

    const size_t stack_size = 1024 * 1024;
    clone_stack stack(stack_size);

    pid_t child_pid = clone(
            child_fn,
            stack.top(),
            SIGCHLD | CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWUTS,
            &cargs);

    // Set up uid/gid map

    auto uid = geteuid();
    auto gid = getegid();

    auto uidmap_cmd = std::ostringstream();
    uidmap_cmd << "newuidmap " << child_pid << " 0 " << uid << " 1";
    int status = system(uidmap_cmd.str().c_str()); // NOLINT(cert-env33-c,concurrency-mt-unsafe)
    if (status < 0) {
        perror("error from system when invoking newuidmap");
        return EXIT_FAILURE;
    }

    auto gidmap_cmd = std::ostringstream();
    gidmap_cmd << "newgidmap " << child_pid << " 0 " << gid << " 1";
    status = system(gidmap_cmd.str().c_str()); // NOLINT(cert-env33-c,concurrency-mt-unsafe)
    if (status < 0) {
        perror("error from system when invoking newgidmap");
        return EXIT_FAILURE;
    }

    // Signal child to continue
    evnt.set();

    // Wait for child
    int child_status;
    auto exited_pid = waitpid(child_pid, &child_status, 0);

    if (exited_pid < 0) {
        perror("error from waitpid");
        return EXIT_FAILURE;
    }

    if (WIFEXITED(child_status)) {
        return WEXITSTATUS(child_status);
    }

    std::cerr << "child status: " << child_status << endl;
    return EXIT_FAILURE;
}
