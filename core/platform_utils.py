from __future__ import annotations

import platform
from dataclasses import dataclass


def detect_os() -> str:
    system_name = platform.system().strip().lower()
    if system_name == "darwin":
        return "macos"
    if system_name.startswith("win"):
        return "windows"
    return "linux"


def detect_architecture() -> str:
    machine = platform.machine().strip().lower()
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    return aliases.get(machine, machine or "x86_64")


@dataclass(frozen=True)
class PlatformInfo:
    os_name: str
    architecture: str


def current_platform() -> PlatformInfo:
    return PlatformInfo(os_name=detect_os(), architecture=detect_architecture())
