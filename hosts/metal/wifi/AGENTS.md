# Wi-Fi diagnostics

- Before selecting a Wi-Fi fix or debug command, inspect the running kernel's
  diagnostic CONFIG flags and the exact driver's implementation. A readable
  `debug_mask` parameter does not prove its debug calls were compiled in.
- Check debug categories and trace formats before enabling them: Linux 7.3's
  ath12k MAC category has key-material dump sites; raw trace events can include
  packet buffers. PCI debugging logs every external interrupt and can flood a
  continuous capture; exclude it from the normal mask. Preserve explicit
  capture/time/storage limits and root-owned,
  read-only-to-operator output. Never simulate firmware crashes during diagnosis.
- Distinguish passive counters from firmware requests: ath12k `get_survey` can
  issue a WMI request and wait for a response. Avoid adding that probe to a
  passive stall capture without explicitly evaluating its effect on the failure.

- Trace-buffer requests are rounded by the kernel. Check the actual
  `buffer_total_size_kb` in the root/tracefs VM fixture against the hard budget.

- Exercise suspend/manual-leave events as well as real link loss when changing
  incident triggers. A local reason-3 leave must not consume a one-incident
  capture and silently leave later wake-time failures without diagnostics.
