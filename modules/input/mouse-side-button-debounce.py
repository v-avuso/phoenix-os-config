"""Fixed-device hardware filter; desktop/Kando policy belongs elsewhere.

Reuse libevdev's cloned capabilities, properties and dropped-event recovery.
Unlike press cooldown, delayed stable releases suppress chatter during long holds.
"""
import argparse
import errno
import os
import select
import signal
import time

SIDE_KEYS = (275, 276)
RELEASE_NS = 180_000_000


class Debouncer:
    def __init__(self):
        self.down = set()
        self.deadlines = {}

    def update(self, code, value, now):
        if code not in SIDE_KEYS:
            return True
        if value == 1:
            self.deadlines.pop(code, None)
            if code in self.down:
                return False
            self.down.add(code)
            return True
        if value == 0:
            if code in self.down:
                # Duplicate releases must not extend the stable-release window.
                self.deadlines.setdefault(code, now + RELEASE_NS)
            return False
        return False

    def due(self, now):
        released = sorted(code for code, deadline in self.deadlines.items() if now >= deadline)
        for code in released:
            self.deadlines.pop(code)
            self.down.discard(code)
        return released

    def timeout(self, now):
        return None if not self.deadlines else max(0, min(self.deadlines.values()) - now) / 1e9

    def clear(self):
        released = sorted(self.down)
        self.down.clear()
        self.deadlines.clear()
        return released


def relay(device, make_output, api, *, clock=time.monotonic_ns, wait=select.select, stopping=lambda: False):
    state = Debouncer()
    output = None
    grabbed = False

    def release(codes):
        if codes:
            output.send_events([api.InputEvent(api.evbit(1, code), 0) for code in codes]
                               + [api.InputEvent(api.SYN_REPORT, 0)])

    def forward(events):
        for event in events:
            now = clock()
            release(state.due(now))
            if event.type != api.EV_KEY or state.update(int(event.code), event.value, now):
                output.send_events([event])

    try:
        output = make_output()
        device.grab()
        grabbed = True
        while not stopping():
            now = clock()
            release(state.due(now))
            readable, _, _ = wait([device.fd], [], [], state.timeout(now))
            if not readable:
                continue
            try:
                forward(device.events())
            except api.EventsDroppedException:
                # libevdev supplies state-difference events after SYN_DROPPED.
                forward(device.sync())
    finally:
        if output is not None:
            try:
                release(state.clear())
            finally:
                try:
                    if grabbed:
                        device.ungrab()
                finally:
                    # libevdev Device has no close() API. Drop the final clone
                    # reference; its managed UinputDevice destroys the node.
                    output = None


def main():
    import libevdev
    parser = argparse.ArgumentParser()
    parser.add_argument("device")
    args = parser.parse_args()
    stopped = False

    def stop(_signum, _frame):
        nonlocal stopped
        stopped = True
        # Interrupt select without waiting indefinitely for another mouse event.
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with open(args.device, "rb", buffering=0) as stream:
        os.set_blocking(stream.fileno(), False)
        device = libevdev.Device(stream)
        if "Razer Viper V2 Pro" not in device.name or not all(device.has(libevdev.evbit(1, code)) for code in SIDE_KEYS):
            raise SystemExit("Declared mouse does not match the reviewed side-button device")
        if not device.has(libevdev.REL_X) or not device.has(libevdev.REL_Y):
            raise SystemExit("Declared mouse lacks pointer axes")
        # The name distinguishes the clone; selecting only the fixed physical
        # by-id path prevents recursive capture of this virtual device.
        device.name = "Phoenix debounced Razer Viper V2 Pro"
        try:
            relay(device, device.create_uinput_device, libevdev, stopping=lambda: stopped)
        except KeyboardInterrupt:
            pass
        except OSError as error:
            if error.errno != errno.ENODEV:
                raise


if __name__ == "__main__":
    main()
