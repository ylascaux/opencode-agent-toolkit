#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, subprocess
from pathlib import Path

TRUTHY={"1","true","yes","on"}
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--major", choices=("1","2"), required=True)
    args=p.parse_args()
    enabled=(os.getenv("OPENCODE_MEMORY_ENABLED") or os.getenv("OAT_MEMORY_ENABLED") or "").lower() in TRUTHY
    if not enabled:
        return 0
    data=Path(os.getenv("XDG_DATA_HOME") or Path.home()/".local/share")
    plugin=Path(os.getenv("OAT_MEMORY_PLUGIN_DIR") or data/"opencode-agent-toolkit/plugins/opencode-memory-plugin")
    vault=Path(os.getenv("OPENCODE_MEMORY_DIR") or os.getenv("OAT_MEMORY_DIR") or data/"opencode-agent-toolkit/memory")
    config=ROOT/("opencode.v2.jsonc" if args.major=="2" else "opencode.jsonc")
    entry=plugin/"dist"/("v2.js" if args.major=="2" else "v1.js")
    if not entry.is_file() or not vault.is_dir():
        print("OpenCode memory unavailable locally; continuing without memory", file=os.sys.stderr)
        return 0
    payload=json.loads(config.read_text())
    key="plugins" if args.major=="2" else "plugin"
    payload[key]=[str(entry.resolve())]
    if args.major=="2" and (plugin/"dist/cli.js").is_file() and shutil.which("node"):
        env=os.environ.copy(); env["OAT_MEMORY_AUTO_SYNC"]="0"; env["OAT_MEMORY_STRICT"]="0"
        for name,spec in payload.get("agents",{}).items():
            try:
                r=subprocess.run(["node",str(plugin/"dist/cli.js"),"render","--agent",name,"--cwd",os.getcwd()],env=env,text=True,capture_output=True,timeout=5)
                if r.returncode==0 and r.stdout.strip(): spec["system"]=spec.get("system","").rstrip()+"\n\n"+r.stdout.strip()+"\n"
            except Exception:
                pass
    config.write_text(json.dumps(payload,indent=2)+"\n")
    return 0

if __name__=="__main__": raise SystemExit(main())
