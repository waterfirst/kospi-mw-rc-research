#!/usr/bin/env python3
"""
Codex local readiness check for the KOSPI contest.

Collects the PC hardware profile and Ollama GPU status so the contest log can
show whether local GLM inference is available on the NVIDIA GPU.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contest" / "codex"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run(command: list[str]) -> str:
    return subprocess.check_output(command, text=True, encoding="utf-8", errors="replace")


def powershell_json(script: str):
    raw = run(["powershell", "-NoProfile", "-Command", script])
    return json.loads(raw)


def main() -> int:
    cpu = powershell_json(
        "Get-CimInstance Win32_Processor | "
        "Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed | ConvertTo-Json"
    )
    mem = powershell_json(
        "Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory | ConvertTo-Json"
    )
    gpus = powershell_json(
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name,AdapterRAM,DriverVersion | ConvertTo-Json"
    )

    try:
        nvidia = run([
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]).strip()
    except Exception as exc:
        nvidia = f"unavailable: {exc}"

    try:
        ollama_list = run(["ollama", "list"]).strip()
        ollama_ps = run(["ollama", "ps"]).strip()
    except Exception as exc:
        ollama_list = f"unavailable: {exc}"
        ollama_ps = f"unavailable: {exc}"

    total_gb = round(int(mem["TotalPhysicalMemory"]) / (1024**3), 1)
    profile = {
        "cpu": cpu,
        "memory_gb": total_gb,
        "gpus": gpus,
        "nvidia_smi": nvidia,
        "ollama_list": ollama_list,
        "ollama_ps": ollama_ps,
        "codex_local_model": "glm4:9b",
        "readiness": {
            "ollama_glm_installed": "glm4:9b" in ollama_list,
            "ollama_glm_on_gpu": "glm4:9b" in ollama_ps and "100% GPU" in ollama_ps,
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "local_readiness.json"
    out_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Codex local readiness")
    print("=====================")
    print(f"CPU     : {cpu['Name']} ({cpu['NumberOfCores']}C/{cpu['NumberOfLogicalProcessors']}T)")
    print(f"Memory  : {total_gb} GB")
    print(f"NVIDIA  : {nvidia}")
    print(f"Ollama  : glm4:9b installed={profile['readiness']['ollama_glm_installed']} "
          f"gpu={profile['readiness']['ollama_glm_on_gpu']}")
    print(f"Saved   : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

