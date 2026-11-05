"""Executed as root in a disposable VM against real tracefs."""
import importlib.util
import logging
from pathlib import Path
import sys
import subprocess
import tempfile

spec = importlib.util.spec_from_file_location('capture', sys.argv[1])
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
global_trace = Path('/sys/kernel/tracing/tracing_on').read_text()
with tempfile.TemporaryDirectory() as directory:
    d.STATE = d.RUNTIME = Path(directory)
    d.MASK.write_text(d.MASK.read_text())
    subprocess.run([sys.argv[2], '-r', 'ath12k'], check=True)
    assert not d.MASK.exists(), 'service must not pin the old sysfs parameter inode'
    subprocess.run([sys.argv[2], 'ath12k'], check=True)
    d.MASK.write_text('0')
    d.setup_trace()
    actual = int((d.TRACE / 'buffer_total_size_kb').read_text())
    print('kernel-reported trace capacity KiB:', actual, flush=True)
    assert actual <= 32768
    for event in d.EVENTS:
        assert (d.TRACE / 'events' / event / 'enable').read_text().strip() == '1'
        fields = (d.TRACE / 'events' / event / 'format').read_text()
        assert '__data_loc u8' not in fields, event  # No raw buffer arrays.
    (d.TRACE / 'trace_marker').write_text('phoenix-wifi-fixture')
    log = logging.getLogger('fixture')
    d.snapshot('incident-before.trace', log)
    assert 'phoenix-wifi-fixture' in (d.STATE / 'incident-before.trace').read_text()
    d.cleanup()
    assert not d.TRACE.exists()
    assert Path('/sys/kernel/tracing/tracing_on').read_text() == global_trace
print('Real tracefs allocation, event formats, snapshot, isolation and cleanup passed')
