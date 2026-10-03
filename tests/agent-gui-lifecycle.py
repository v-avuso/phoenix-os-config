#!/usr/bin/env python3
"""Guard the Linux tray-close patch against upstream wiring drift."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gui_lifecycle", ROOT / "modules/development/ai/agent/gui-lifecycle.py")
patcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patcher)

# Short excerpts from the pinned desktop 26.930.31730 main/bootstrap bundles.
PREDICATE = "function Z9(){return Y9&&G9?.isReady()===!0}"
CLOSE = ("R.on(`close`,e=>{if(!this.isAppQuitting&&this.isMainWindow(R)&&"
         "this.windowCloseConfirmation.shouldPreventClose(R)){e.preventDefault();return}"
         "this.persistPrimaryWindowBounds(R);let t=this.getPrimaryWindows().some(e=>e!==R);"
         "if((process.platform===`win32`||process.platform===`linux`)&&!this.isAppQuitting&&"
         "this.options.canHideLastWindowToTray?.()===!0&&!t){e.preventDefault(),R.hide();return}});")
BOOTSTRAP = ("exports.u=DTe;var M9=()=>!1;"
             "function ETe(){p.app.on(`window-all-closed`,()=>{process.platform!==`win32`&&"
             "(process.platform===`darwin`&&p.app.isPackaged||process.platform===`linux`&&M9()||"
             "p.app.quit())})}function DTe(e){M9=e}")
REGISTER = ("registerWindow(w,host,primary,appearance,mode){primary&&this.trackPrimaryWindow(w);"
            "w.on(`closed`,()=>{this.forgetWebContents(o),this.windowAppearances.delete(a),"
            "primary&&(this.primaryWindows.delete(w),this.lastActivePrimaryWindow===w&&"
            "(this.lastActivePrimaryWindow=null),this.emitPrimaryWindowChangeIfNeeded())}),"
            "mode===`register`&&this.options.onWindowRegistered?.(w)}"
            "trackPrimaryWindow(w){this.primaryWindows.add(w)}")


def fixture(root, names=None):
    names = names or dict(pred="Z9", visible="Y9", window="G9", module="m",
                          setter="DTe", state="M9", app="p", bootstrap="D3_zvIvQ")
    build = root / ".vite" / "build"
    build.mkdir(parents=True)
    predicate = PREDICATE.replace("Z9", names["pred"]).replace("Y9", names["visible"]).replace("G9", names["window"])
    close = CLOSE
    main = (f'const {names["module"]}=require("./bootstrap-{names["bootstrap"]}.js");'
            f'let {names["app"]}=require("electron"),x=e.a({names["app"]},1);'
            f'{names["app"]}=e.a({names["app"]});'
            f'function quitApp(){{{names["app"]}.app.quit()}}'
            + predicate + f'const options={{canHideLastWindowToTray:{names["pred"]}}};'
            + close + f'function install(){{{names["module"]}.u({names["pred"]})}}')
    main += REGISTER
    bootstrap = (BOOTSTRAP.replace("DTe", names["setter"]).replace("M9", names["state"])
                 .replace("D3_zvIvQ", names["bootstrap"]).replace("p.app", names["app"] + ".app"))
    main_path = build / "main-lifecycle.js"
    bootstrap_path = build / f'bootstrap-{names["bootstrap"]}.js'
    main_path.write_text(main)
    bootstrap_path.write_text(bootstrap)
    return main_path, bootstrap_path


class LifecyclePatch(unittest.TestCase):
    def test_original_and_renamed_minified_identifiers(self):
        variants = [
            None,
            dict(pred="trayReady", visible="appVisible", window="mainWin", module="bootstrap",
                 setter="setKeepalive", state="keepalive", app="electron", bootstrap="boot_ABC123"),
        ]
        for names in variants:
            with self.subTest(names=names), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                main, bootstrap = fixture(root, names)
                original = main.read_text()
                self.assertEqual(patcher.patch(root), main)
                changed = main.read_text()
                pred_name = (names or {}).get("pred", "Z9")
                self.assertIn(f"function {pred_name}(){{return process.platform!==`linux`&&", changed)
                self.assertIn("process.platform===`linux`&&!this.isAppQuitting&&this.getPrimaryWindows().length===0&&", changed)
                self.assertEqual(changed.count("shouldPreventClose"), 1)
                self.assertEqual(changed.count("persistPrimaryWindowBounds"), 1)
                self.assertEqual(changed.count("canHideLastWindowToTray?.()===!0"), 1)
                self.assertIn("window-all-closed", bootstrap.read_text())
                if shutil.which("node"):
                    app_name = (names or {}).get("app", "p")
                    branch = re_patched_cleanup(changed, app_name)
                    behavior = ("const vm=require('node:vm'),assert=require('node:assert/strict');"
                                "let quits=0;const sandbox={process:{platform:'linux'}};"
                                f"sandbox.{app_name}={{app:{{quit(){{quits++;return true}}}}}};"
                                f"const run=vm.runInNewContext('(function(primary,w){{return {branch}}})',sandbox);"
                                "function check(platform,quitting,remaining,primary,expected){"
                                "sandbox.process.platform=platform;quits=0;const w={},ctx={isAppQuitting:quitting,"
                                "primaryWindows:new Set([w]),lastActivePrimaryWindow:w,"
                                "emitPrimaryWindowChangeIfNeeded(){},getPrimaryWindows(){return remaining? [{}]:[]}};"
                                "assert.equal(run.call(ctx,primary,w),expected);assert.equal(quits,expected?1:0)}"
                                "check('linux',false,false,true,true);check('linux',false,true,true,false);"
                                "check('win32',false,false,true,false);check('linux',true,false,true,false);"
                                "check('linux',false,false,false,false);")
                    subprocess.run([shutil.which("node"), "-e", behavior], check=True,
                                   capture_output=True, text=True)
                    values = names or dict(pred="Z9", visible="Y9", window="G9")
                    # Read the patched function itself; Node supplies platform and dependencies.
                    function = re_patched(changed, pred_name)
                    script = ("const vm=require('node:vm'),assert=require('node:assert/strict');"
                              f"const c={{process:{{platform:'linux'}},{values.get('visible','Y9')}:true,"
                              f"{values.get('window','G9')}:{{isReady:()=>true}}}};"
                              f"vm.runInNewContext({json.dumps(function+';globalThis.f='+pred_name+';')},c);"
                              "assert.equal(c.f(),false);c.process.platform='win32';assert.equal(c.f(),true);"
                              f"c.{values.get('visible','Y9')}=false;assert.equal(c.f(),false);")
                    subprocess.run([shutil.which("node"), "-e", script], check=True,
                                   capture_output=True, text=True)

    def test_invalid_shapes_fail_before_any_write(self):
        for failure in ("absent", "duplicate", "broken-bootstrap", "broken-window-consumer",
                        "broken-primary-cleanup", "wrong-closed-receiver", "cleanup-outside-listener",
                        "missing-electron-import"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                main, bootstrap = fixture(root)
                source = main.read_text()
                boot = bootstrap.read_text()
                if failure == "absent":
                    source = source.replace(PREDICATE, "function Z9(){return true}")
                elif failure == "duplicate":
                    source += "function duplicate(){return Y9&&G9?.isReady()===!0}"
                elif failure == "broken-bootstrap":
                    source = source.replace("m.u(Z9)", "m.u(elsewhere)")
                elif failure == "broken-primary-cleanup":
                    source = source.replace("this.primaryWindows.delete(w)", "this.otherWindows.delete(w)")
                elif failure == "wrong-closed-receiver":
                    source = source.replace("w.on(`closed`", "other.on(`closed`")
                elif failure == "cleanup-outside-listener":
                    source = source.replace("w.on(`closed`,()=>{", "w.on(`closed`,()=>{});{")
                elif failure == "missing-electron-import":
                    source = source.replace('let p=require("electron")', 'let other={}')
                else:
                    boot = boot.replace("M9()", "other()")
                    bootstrap.write_text(boot)
                main.write_text(source)
                before_main, before_bootstrap = main.read_bytes(), bootstrap.read_bytes()
                with self.assertRaises(ValueError):
                    patcher.patch(root)
                self.assertEqual(main.read_bytes(), before_main)
                self.assertEqual(bootstrap.read_bytes(), before_bootstrap)
                self.assertEqual(list(main.parent.glob("main-lifecycle.js.*")), [])


def re_patched(source, name):
    import re
    match = re.search(rf"function {re.escape(name)}\(\)\{{return process\.platform!==`linux`&&[^}}]+\}}", source)
    if match is None:
        raise AssertionError("patched predicate was not found")
    return match.group(0)


def re_patched_cleanup(source, app):
    import re
    match = re.search(r"primary&&\(this\.primaryWindows\.delete\(w\).*?" +
                      re.escape(app) + r"\.app\.quit\(\)\)", source)
    if match is None:
        raise AssertionError("patched last-primary cleanup branch was not found")
    return match.group(0)


if __name__ == "__main__":
    unittest.main()
