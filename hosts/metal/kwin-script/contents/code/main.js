// KWin emits screensChanged when outputs are connected or removed.
workspace.screensChanged.connect(function () {
    callDBus(
        "org.freedesktop.systemd1",
        "/org/freedesktop/systemd1",
        "org.freedesktop.systemd1.Manager",
        "StartUnit",
        "phoenix-monitor-layout.service",
        "replace"
    );
});
