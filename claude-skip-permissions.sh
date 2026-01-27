#!/bin/bash
# Claude CLI with dangerously-skip-permissions flag
# This shell script runs Claude without permission checks

claude --dangerously-skip-permissions "$@"
