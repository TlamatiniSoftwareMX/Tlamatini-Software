#!/usr/bin/env bash
set -euo pipefail
# Linux 5.2.6, Gemma 3 4B, RAM recomendada: 8 GB.
curl -fsSL --retry 3 https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/download/ediciones-2026-11-13/INSTALAR-TLAMATINI-EDICIONES.sh | bash -s -- ia-8gb "$@"
