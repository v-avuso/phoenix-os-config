"""Internal transient-unit launcher; no privileged public entry point."""
import os
import sys
# Preserve installed argv[0] for immutable multicall ELF applets.
os.execve(sys.argv[1], sys.argv[2:], {'PATH':'/nonexistent','HOME':'/var/empty','LANG':'C'})
