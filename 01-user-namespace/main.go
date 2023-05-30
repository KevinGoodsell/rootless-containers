package main

// The first step creates a user namespace and runs a command in it. The command
// is provided on the command line.

import (
	"os"
	"os/exec"
	"syscall"
)

func must(err error) {
	if err != nil {
		panic(err)
	}
}

func main() {
	if len(os.Args) < 2 {
		panic("Needs at least 1 arg")
	}
	cmd := exec.Command(os.Args[1], os.Args[2:]...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Cloneflags: syscall.CLONE_NEWUSER,
	}

	must(cmd.Run())
}
