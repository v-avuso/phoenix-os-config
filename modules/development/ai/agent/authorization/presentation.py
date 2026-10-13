"""Native explanation only; credentials stay with the existing Polkit agent."""
import html
import json
import subprocess

class Unavailable(ValueError): pass
class Cancelled(ValueError): pass

def show(settings, request, source=None):
    operation = request["operation"]
    if operation.startswith("deployment."):
        command = "phoenix-" + operation.removeprefix("deployment.")
        why = "AI security review is disabled. Installed policy requires native operator authentication."
    else:
        command = "phoenix-admin " + operation.removeprefix("admin.")
        why = "Installed diagnostic policy requires native operator authentication."
    rows = [("Command",command), ("Operation",operation),
            ("Arguments",json.dumps(request["arguments"],ensure_ascii=False,sort_keys=True)),
            ("Task",request["task"]), ("Reason",request["reason"]),
            ("Broker decision","human: authentication required"), ("Why",why)]
    if source is not None: rows.insert(3,("Selected source",source))
    body = "\n\n".join("<b>" + label + ":</b> " + html.escape(value) for label,value in rows)
    body += "\n\nContinue opens native authentication. Cancelling stops this request."
    try:
        result = subprocess.run([settings["program"],"--question","--default-cancel",
            "--title=Phoenix authorization request", "--width=640",
            "--ok-label=Continue to authentication", "--cancel-label=Cancel request", "--text="+body],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            timeout=300,check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Unavailable("context-unavailable") from None
    if result.returncode == 1: raise Cancelled("context-cancelled")
    if result.returncode != 0: raise Unavailable("context-unavailable")
