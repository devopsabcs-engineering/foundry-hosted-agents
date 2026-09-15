import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
LABS = sorted((ROOT / "docs/labs").glob("lab-*.md")) + [ROOT / "docs/private-networking.md"]
PWSH = shutil.which("pwsh")


def powershell_blocks(path):
    return re.findall(r"(?ms)^```powershell\n(.*?)^```", path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("english", LABS, ids=lambda path: path.stem)
def test_bilingual_powershell_commands_match(english):
    french = ROOT / "docs/fr" / english.relative_to(ROOT / "docs")

    def commands(path):
        return [[line.strip() for line in block.splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
                for block in powershell_blocks(path)]

    assert commands(english) == commands(french)


@pytest.mark.skipif(PWSH is None, reason="PowerShell 7 is required for syntax checks")
@pytest.mark.parametrize("english", LABS, ids=lambda path: path.stem)
def test_workshop_powershell_syntax(english):
    for path in (english, ROOT / "docs/fr" / english.relative_to(ROOT / "docs")):
        for block in powershell_blocks(path):
            command = (
                "$parseErrors = $null; "
                "[void][System.Management.Automation.Language.Parser]::ParseInput("
                "$env:WORKSHOP_BLOCK, [ref]$null, [ref]$parseErrors); "
                "if ($parseErrors) { $parseErrors | Out-String | Write-Error; exit 1 }"
            )
            result = subprocess.run(
                [PWSH, "-NoProfile", "-NonInteractive", "-Command", command],
                env={**os.environ, "WORKSHOP_BLOCK": block},
                capture_output=True, text=True, timeout=30, check=False,
            )
            assert result.returncode == 0, f"{path.name}: {result.stdout}{result.stderr}"
