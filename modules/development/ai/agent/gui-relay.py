"""Socket-activated fixed app-server relay; never accepts a host command."""
import os
import subprocess
import sys
import threading


def relay(config):
    # systemd supplies the accepted full-duplex socket on stdin/stdout.
    # Only this immutable command can run, irrespective of client bytes.
    process = subprocess.Popen(
        [config["python"], "-I", config["launcher"], config["launcher_config"],
         "app-server", "--analytics-default-enabled"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
        cwd=config["workdir"], env={"HOME": config["home"],
            "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}",
            "PATH": config["path"]})

    def input_stream():
        try:
            while chunk := os.read(0, 65536):
                process.stdin.write(chunk)
                process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        finally:
            process.stdin.close()

    threading.Thread(target=input_stream, daemon=True).start()
    try:
        while chunk := os.read(process.stdout.fileno(), 65536):
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    import json
    with open(sys.argv[1]) as stream:
        relay(json.load(stream))
