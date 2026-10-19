import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"
MAKE = shutil.which("make")
MOCK = """#!{python}
import json
import os
from pathlib import Path
import shutil
import sys

name = Path(sys.argv[0]).name
with open(os.environ['BOOTSTRAP_TEST_LOG'], 'a') as log:
    log.write(json.dumps([name, *sys.argv[1:]]) + '\\n')
if name == 'apt-get' and sys.argv[1:] == ['install', '--yes', 'extrepo']:
    shutil.copyfile(__file__, Path(__file__).with_name('extrepo'))
    Path(__file__).with_name('extrepo').chmod(0o755)
if name == 'extrepo' and sys.argv[-1] == os.environ.get('FAIL_REPOSITORY'):
    print('Repository does not exist!', file=sys.stderr)
    sys.exit(23)
if name == 'apt-get' and sys.argv[1] == os.environ.get('FAIL_APT_COMMAND'):
    print('APT failed!', file=sys.stderr)
    sys.exit(100)
if name == 'apt' and sys.argv[1:] == ['list']:
    print('Mock APT manifest')
"""


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        shutil.copyfile(MAKEFILE, self.root / "Makefile")
        (self.root / "apt-repos.txt").write_text("protonvpn\nyarnpkg\n")
        (self.root / "aptfile.txt").write_text("git\ncurl\n")
        (self.bin / "sudo").write_text('#!/bin/bash\nexec "$@"\n')
        (self.bin / "sudo").chmod(0o755)
        self.write_tool("apt-get")
        self.write_tool("apt")
        self.log = self.root / "commands.jsonl"
        self.env = {
            **os.environ,
            "PATH": str(self.bin),
            "BOOTSTRAP_TEST_LOG": str(self.log),
        }
        self.env.pop("FAIL_REPOSITORY", None)
        self.env.pop("FAIL_APT_COMMAND", None)
        for name in ("MAKEFLAGS", "MFLAGS", "MAKELEVEL"):
            self.env.pop(name, None)

    def write_tool(self, name):
        tool = self.bin / name
        tool.write_text(MOCK.format(python=sys.executable))
        tool.chmod(0o755)

    def run_bootstrap(self):
        return subprocess.run(
            [MAKE, "--no-print-directory", "--silent", "-C", str(self.root), "install"],
            cwd="/",
            env=self.env,
            capture_output=True,
            text=True,
        )

    def commands(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_installs_extrepo_before_enabling_and_refreshing_sources(self):
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [
            ["apt-get", "update"],
            ["apt-get", "install", "--yes", "extrepo"],
            ["extrepo", "enable", "protonvpn"],
            ["extrepo", "enable", "yarnpkg"],
            ["apt-get", "update"],
            ["apt-get", "install", "--yes", "--", "git", "curl"],
            ["apt", "list"],
        ])
        self.assertEqual(
            (self.root / "aptfile.manifest").read_text(), "Mock APT manifest\n"
        )

    def test_repeated_runs_enable_every_repository_again(self):
        self.write_tool("extrepo")
        first = self.run_bootstrap()
        second = self.run_bootstrap()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        expected = [
            ["extrepo", "enable", "protonvpn"],
            ["extrepo", "enable", "yarnpkg"],
            ["apt-get", "update"],
            ["apt-get", "install", "--yes", "--", "git", "curl"],
            ["apt", "list"],
        ]
        self.assertEqual(self.commands(), expected * 2)

    def test_whitespace_comments_crlf_and_final_line_without_newline(self):
        self.write_tool("extrepo")
        (self.root / "apt-repos.txt").write_bytes(
            b"  # ignored\r\n\t\r\n  protonvpn \r\nyarnpkg"
        )
        (self.root / "aptfile.txt").write_bytes(
            b"\t# ignored\r\n\r\n git \r\n libgl1:i386"
        )
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [
            ["extrepo", "enable", "protonvpn"],
            ["extrepo", "enable", "yarnpkg"],
            ["apt-get", "update"],
            ["apt-get", "install", "--yes", "--", "git", "libgl1:i386"],
            ["apt", "list"],
        ])

    def test_failed_repository_stops_before_package_installation(self):
        self.write_tool("extrepo")
        self.env["FAIL_REPOSITORY"] = "protonvpn"
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("protonvpn from apt-repos.txt", result.stderr)
        self.assertEqual(self.commands(), [["extrepo", "enable", "protonvpn"]])
        self.assertFalse((self.root / "aptfile.manifest").exists())

    def test_missing_package_list_fails_before_any_system_command(self):
        (self.root / "aptfile.txt").unlink()
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("aptfile.txt", result.stderr)
        self.assertEqual(self.commands(), [])

    def test_apt_failures_stop_before_writing_manifest(self):
        self.write_tool("extrepo")
        for command in ("update", "install"):
            with self.subTest(command=command):
                self.log.unlink(missing_ok=True)
                self.env["FAIL_APT_COMMAND"] = command
                result = self.run_bootstrap()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("APT failed!", result.stderr)
                self.assertEqual(self.commands()[-1][0:2], ["apt-get", command])
                self.assertFalse((self.root / "aptfile.manifest").exists())

    def test_empty_lists_do_not_run_bare_package_install(self):
        self.write_tool("extrepo")
        (self.root / "apt-repos.txt").write_text("# no repositories\n")
        (self.root / "aptfile.txt").write_text("  # no packages\n\n")
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [["apt-get", "update"], ["apt", "list"]])


if __name__ == "__main__":
    unittest.main()
