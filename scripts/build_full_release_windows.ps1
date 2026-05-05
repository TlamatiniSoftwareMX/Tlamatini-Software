$env:TLAMATINI_SKIP_RUNTIME_VERIFY = if ($env:TLAMATINI_SKIP_RUNTIME_VERIFY) { $env:TLAMATINI_SKIP_RUNTIME_VERIFY } else { "0" }
python scripts/local_ai_tool.py build_full_release
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/local_ai_tool.py package_full_release
exit $LASTEXITCODE
