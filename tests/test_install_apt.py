import hashlib
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
STOW = shutil.which("stow")
MOCK = """#!{python}
import json
import os
from pathlib import Path
import shutil
import sys

name = Path(sys.argv[0]).name
if name == 'dpkg' and sys.argv[1:] == ['--print-architecture']:
    print('amd64')
    sys.exit(0)
if name == 'dpkg-query':
    sys.stdout.write(os.environ.get('CLAUDE_STATUS', '') if sys.argv[-1] == 'claude-code' else os.environ.get('NVIDIA_PACKAGES', ''))
    sys.exit(0)
with open(os.environ['BOOTSTRAP_TEST_LOG'], 'a') as log:
    log.write(json.dumps([name, *sys.argv[1:]]) + '\\n')
if name == 'node' and os.environ.get('FAIL_NODE') == '1':
    print('AI tools require Node.js 22.19 or newer.', file=sys.stderr)
    sys.exit(1)
if name == 'npm' and sys.argv[1] == 'install':
    prefix = Path(sys.argv[sys.argv.index('--prefix') + 1])
    for tool, package in [('codex', '@openai/codex'), ('pi', '@earendil-works/pi-coding-agent'), ('claude', '@anthropic-ai/claude-code')]:
        binary = prefix / 'lib/node_modules' / package / 'cli'
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text('#!/bin/sh\\nprintf "npm agent version\\\\n"\\n')
        binary.chmod(0o755)
        launcher = prefix / 'bin' / tool
        launcher.unlink(missing_ok=True)
        launcher.symlink_to(binary)
    if os.environ.get('FAIL_NPM') == '1':
        print('npm install failed', file=sys.stderr)
        sys.exit(1)
if name == 'curl':
    Path(sys.argv[sys.argv.index('--output') + 1]).write_text(os.environ.get('BOOK_DOWNLOAD_CONTENT', 'test package'))
if name == 'apt-get' and sys.argv[1] == 'install' and sys.argv[-1].endswith('.deb'):
    package = Path(sys.argv[-1])
    with open(os.environ['STAGED_PACKAGE_LOG'], 'a') as log:
        log.write(json.dumps(dict(path=str(package), contents=package.read_text(), file_mode=package.stat().st_mode & 0o777, directory_mode=package.parent.stat().st_mode & 0o777)) + '\\n')
    if os.environ.get('FAIL_LOCAL_PACKAGE') == '1':
        sys.exit(100)
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
if name == 'mountpoint':
    sys.exit(1)
if name == 'systemctl' and sys.argv[1:] == ['is-active', '--quiet', 'nix-daemon.service']:
    sys.exit(0 if os.environ.get('NIX_DAEMON_ACTIVE') == '1' else 3)
"""


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        shutil.copyfile(MAKEFILE, self.root / "Makefile")
        shutil.copytree(MAKEFILE.parent / "sources", self.root / "sources")
        shutil.copytree(MAKEFILE.parent / "config", self.root / "config")
        shutil.copytree(MAKEFILE.parent / "stow", self.root / "stow")
        for tool in ("install", "mktemp", "rm", "sed", "cmp", "cp", "grep", "git", "awk", "cat", "date", "sha256sum", "mv", "chmod", "readlink"):
            (self.bin / tool).symlink_to(shutil.which(tool))
        (self.bin / "python3").symlink_to(sys.executable)
        if STOW:
            (self.bin / "stow").symlink_to(STOW)
        (self.root / "apt-repos.txt").write_text("protonvpn\nyarnpkg\n")
        (self.root / "aptfile.txt").write_text("git\ncurl\n")
        (self.bin / "sudo").write_text('#!/bin/bash\nif [[ $1 == install && ${@: -1} == /srv/data ]]; then exit 0; fi\nexec "$@"\n')
        (self.bin / "sudo").chmod(0o755)
        self.write_tool("apt-get")
        self.write_tool("apt")
        self.write_tool("dpkg")
        self.write_tool("dpkg-query")
        self.log = self.root / "commands.jsonl"
        self.env = {
            **os.environ,
            "PATH": str(self.bin),
            "BOOTSTRAP_TEST_LOG": str(self.log),
            "HOME": str(self.root),
            "XDG_CONFIG_HOME": str(self.root / ".config"),
            "XDG_DATA_HOME": str(self.root / ".local/share"),
            "XDG_CACHE_HOME": str(self.root / ".cache"),
            "STAGED_PACKAGE_LOG": str(self.root / "staged-packages.jsonl"),
        }
        self.env.pop("FAIL_REPOSITORY", None)
        self.env.pop("FAIL_APT_COMMAND", None)
        self.env.pop("NIX_DAEMON_ACTIVE", None)
        self.env.pop("FAIL_LOCAL_PACKAGE", None)
        self.env.pop("BOOK_DOWNLOAD_CONTENT", None)
        for name in ("CLAUDE_STATUS", "FAIL_NODE", "FAIL_NPM"):
            self.env.pop(name, None)
        for name in ("MAKEFLAGS", "MFLAGS", "MAKELEVEL"):
            self.env.pop(name, None)

    def write_tool(self, name):
        tool = self.bin / name
        tool.write_text(MOCK.format(python=sys.executable))
        tool.chmod(0o755)

    def run_bootstrap(self, target="install", *variables):
        return subprocess.run(
            [MAKE, "--no-print-directory", "--silent", "-C", str(self.root),
             f"APT_SOURCE_DIR={self.root / 'apt-sources'}",
             f"APT_KEY_DIR={self.root / 'apt-keys'}",
             f"VENDOR_KEY_DIR={self.root / 'vendor-keys'}", *variables, target],
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

    def test_sources_use_ubuntu_suite_and_official_vendor_key_paths(self):
        result = self.run_bootstrap("sources-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        docker = (self.root / "apt-sources/docker.sources").read_text()
        self.assertIn("Suites: resolute", docker)
        self.assertIn("https://download.docker.com/linux/ubuntu", docker)
        self.assertNotIn("@UBUNTU_CODENAME@", docker)
        signal = (self.root / "apt-sources/signal-desktop.sources").read_text()
        self.assertIn("https://updates.signal.org/desktop/apt", signal)
        self.assertIn("Signed-By: /usr/share/keyrings/signal-desktop-keyring.gpg", signal)
        self.assertTrue((self.root / "vendor-keys/signal-desktop-keyring.gpg").is_file())
        self.assertEqual(self.commands(), [])

    @unittest.skipUnless(STOW, "Install GNU Stow to test config links")
    def test_config_install_backs_up_existing_file_and_is_repeatable(self):
        self.write_tool("extrepo")
        target = self.root / ".config/kitty/kitty.conf"
        target.parent.mkdir(parents=True)
        target.write_text("font_size 10\n")
        for _ in range(2):
            result = self.run_bootstrap("kitty-install")
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(), self.root / "stow/kitty/kitty/kitty.conf")
        self.assertEqual(target.with_name("kitty.conf.deps-backup").read_text(), "font_size 10\n")
        self.assertEqual(len(list(target.parent.glob("*.deps-backup*"))), 1)

    @unittest.skipUnless(STOW, "Install GNU Stow to test config links")
    def test_git_include_preserves_existing_config_and_is_not_duplicated(self):
        self.write_tool("extrepo")
        gitconfig = self.root / ".gitconfig"
        gitconfig.write_text("[alias]\n\tst = status\n")
        for _ in range(2):
            result = self.run_bootstrap("git-install")
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("st = status", gitconfig.read_text())
        self.assertEqual(gitconfig.read_text().count("deps.config"), 1)
        self.assertEqual((self.root / ".gitconfig.deps-backup").read_text(), "[alias]\n\tst = status\n")

    @unittest.skipUnless(STOW, "Install GNU Stow to test config links")
    def test_dotfiles_links_all_configs_without_system_commands_or_folded_directories(self):
        result = self.run_bootstrap("dotfiles")
        self.assertEqual(result.returncode, 0, result.stderr)
        paths = {
            ".config/nvim/init.lua": "nvim/nvim/init.lua",
            ".config/kitty/kitty.conf": "kitty/kitty/kitty.conf",
            ".config/nix/nix.conf": "nix/nix/nix.conf",
            ".config/git/deps.config": "git/git/deps.config",
            ".zshrc": "shell/.zshrc",
        }
        for target, source in paths.items():
            link = self.root / target
            self.assertTrue(link.is_symlink(), target)
            self.assertEqual(link.resolve(), self.root / "stow" / source)
            self.assertFalse(link.parent.is_symlink())
        self.assertIn("deps.config", (self.root / ".gitconfig").read_text())
        generated = self.root / ".config/nvim/pack/plugins/start/generated"
        generated.mkdir(parents=True)
        result = self.run_bootstrap("dotfiles")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(generated.is_dir())
        self.assertFalse((self.root / "stow/nvim/nvim/pack").exists())
        self.assertEqual(self.commands(), [])

    @unittest.skipUnless(STOW, "Install GNU Stow to test config links")
    def test_dotfiles_respects_custom_config_home(self):
        config_home = self.root / "custom-config"
        result = self.run_bootstrap("dotfiles", f"CONFIG_HOME={config_home}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((config_home / "kitty/kitty.conf").resolve(), self.root / "stow/kitty/kitty/kitty.conf")
        self.assertTrue((self.root / ".zshrc").is_symlink())

    @unittest.skipUnless(STOW, "Install GNU Stow to test config links")
    def test_dotfiles_refuses_to_modify_another_config_checkout(self):
        other = self.root / "other-checkout"
        other.mkdir()
        (other / "init.lua").write_text("existing config\n")
        (self.root / ".config").mkdir()
        (self.root / ".config/nvim").symlink_to(other, target_is_directory=True)
        result = self.run_bootstrap("dotfiles")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Config directory is already a symlink", result.stderr)
        self.assertEqual((other / "init.lua").read_text(), "existing config\n")
        self.assertFalse((other / "init.lua.deps-backup").exists())

    def test_missing_stow_fails_without_system_commands(self):
        (self.bin / "stow").unlink(missing_ok=True)
        result = self.run_bootstrap("dotfiles")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sudo apt install stow", result.stderr)
        self.assertEqual(self.commands(), [])

    @unittest.skipUnless(STOW, "Install GNU Stow to test config links")
    def test_nix_preserves_active_daemon_and_still_links_config(self):
        self.write_tool("extrepo")
        self.write_tool("nix")
        self.write_tool("systemctl")
        self.env["NIX_DAEMON_ACTIVE"] = "1"
        result = self.run_bootstrap("nix-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Using the existing active Nix daemon", result.stdout)
        self.assertEqual([cmd for cmd in self.commands() if cmd[0] == "systemctl"], [
            ["systemctl", "is-active", "--quiet", "nix-daemon.service"],
        ])
        self.assertEqual([cmd for cmd in self.commands() if cmd[0:2] == ["apt-get", "install"]], [
            ["apt-get", "install", "--yes", "direnv"],
        ])
        self.assertEqual((self.root / ".config/nix/nix.conf").resolve(), self.root / "stow/nix/nix/nix.conf")

    @unittest.skipUnless(STOW, "Install GNU Stow to test config links")
    def test_nix_starts_socket_when_daemon_is_inactive(self):
        self.write_tool("extrepo")
        self.write_tool("nix")
        self.write_tool("systemctl")
        result = self.run_bootstrap("nix-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([cmd for cmd in self.commands() if cmd[0] == "systemctl"], [
            ["systemctl", "is-active", "--quiet", "nix-daemon.service"],
            ["systemctl", "enable", "--now", "nix-daemon.socket"],
        ])

    def prepare_book_package(self, cached=True):
        self.write_tool("extrepo")
        self.write_tool("flatpak")
        self.write_tool("curl")
        self.root.chmod(0o700)
        package = self.root / ".cache/deps/debs/OpenAudible.deb"
        package.parent.mkdir(parents=True)
        checksum = hashlib.sha256(b"test package").hexdigest()
        (self.root / "book-debs.txt").write_text(f"openaudible https://example.invalid/OpenAudible.deb {checksum}\n")
        if cached:
            package.write_text("test package")
            package.chmod(0o600)
        return package

    def test_books_stages_verified_cache_for_apt_and_cleans_up(self):
        cached = self.prepare_book_package()
        result = self.run_bootstrap("books-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        staged = json.loads((self.root / "staged-packages.jsonl").read_text())
        path = Path(staged["path"])
        self.assertEqual(path.parent.parent, Path("/tmp"))
        self.assertEqual(staged["contents"], "test package")
        self.assertEqual(staged["file_mode"], 0o644)
        self.assertEqual(staged["directory_mode"], 0o755)
        self.assertFalse(path.parent.exists())
        self.assertEqual(cached.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertFalse(any(cmd[0] == "curl" for cmd in self.commands()))

    def test_books_rejects_bad_download_before_local_package_install(self):
        self.prepare_book_package(cached=False)
        self.env["BOOK_DOWNLOAD_CONTENT"] = "wrong package"
        result = self.run_bootstrap("books-install")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "staged-packages.jsonl").exists())

    def test_books_removes_staging_directory_when_apt_fails(self):
        self.prepare_book_package()
        self.env["FAIL_LOCAL_PACKAGE"] = "1"
        result = self.run_bootstrap("books-install")
        self.assertNotEqual(result.returncode, 0)
        staged = json.loads((self.root / "staged-packages.jsonl").read_text())
        self.assertFalse(Path(staged["path"]).parent.exists())

    def prepare_ai_migration(self):
        self.write_tool("node")
        self.write_tool("npm")
        shutil.copyfile(MAKEFILE.parent / "ai-tools.txt", self.root / "ai-tools.txt")
        self.legacy_ai = self.root / ".local/share/deps/ai-tools"
        self.ai_cache = self.root / ".cache/deps/ai-tools"
        self.ai_cache.mkdir(parents=True)
        (self.ai_cache / "download.tar.gz").write_text("cached archive")
        launchers = self.root / ".local/bin"
        launchers.mkdir(parents=True)
        for name in ("codex", "pi"):
            binary = self.legacy_ai / name / "1.0" / name
            binary.parent.mkdir(parents=True)
            binary.write_text("old agent")
            (launchers / name).symlink_to(binary)
        (launchers / "claude").write_text("old manual launcher")
        for name in ("apt-sources", "apt-keys"):
            (self.root / name).mkdir()
        self.claude_source = self.root / "apt-sources/claude-code.sources"
        self.claude_key = self.root / "apt-keys/claude-code.asc"
        self.claude_source.write_text("old Claude repository")
        self.claude_key.write_text("old public key")
        self.agent_data = [".codex/state.sqlite", ".codex/auth.json", ".claude/settings.json", ".claude.json", ".pi/agent/sessions/session.jsonl"]
        for name in self.agent_data:
            file = self.root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("private agent data")
        self.env["CLAUDE_STATUS"] = "installed"

    def test_ai_reinstall_installs_npm_before_cleaning_and_preserves_agent_data(self):
        self.prepare_ai_migration()
        result = self.run_bootstrap("ai-reinstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        prefix = self.root / ".local"
        npm = ["npm", "install", "--global", "--prefix", str(prefix), "--include=optional", "--", "@openai/codex@latest", "@earendil-works/pi-coding-agent@latest", "@anthropic-ai/claude-code@latest"]
        remove = ["apt-get", "remove", "--yes", "claude-code"]
        self.assertLess(self.commands().index(npm), self.commands().index(remove))
        for tool, package in [("codex", "@openai/codex"), ("pi", "@earendil-works/pi-coding-agent"), ("claude", "@anthropic-ai/claude-code")]:
            self.assertEqual((prefix / "bin" / tool).resolve(), prefix / "lib/node_modules" / package / "cli")
        self.assertFalse(self.legacy_ai.exists())
        self.assertFalse(self.ai_cache.exists())
        self.assertFalse(self.claude_source.exists())
        self.assertFalse(self.claude_key.exists())
        for name in self.agent_data:
            self.assertEqual((self.root / name).read_text(), "private agent data")
        result = self.run_bootstrap("ai-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((prefix / "bin/codex.deps-backup.~1~").exists())

    def test_ai_reinstall_restores_launchers_and_skips_cleanup_when_npm_fails(self):
        self.prepare_ai_migration()
        old_codex = (self.root / ".local/bin/codex").resolve()
        self.env["FAIL_NPM"] = "1"
        result = self.run_bootstrap("ai-reinstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / ".local/bin/codex").resolve(), old_codex)
        self.assertEqual((self.root / ".local/bin/claude").read_text(), "old manual launcher")
        self.assertTrue(self.legacy_ai.exists())
        self.assertTrue(self.ai_cache.exists())
        self.assertTrue(self.claude_source.exists())
        self.assertFalse(any(cmd[0] == "apt-get" for cmd in self.commands()))

    def test_ai_reinstall_requires_toolchain_before_touching_old_installations(self):
        self.prepare_ai_migration()
        (self.bin / "node").unlink()
        result = self.run_bootstrap("ai-reinstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Activate your Node.js/npm toolchain", result.stderr)
        self.assertTrue(self.legacy_ai.exists())
        self.assertTrue((self.root / ".local/bin/codex").is_symlink())
        self.assertEqual(self.commands(), [])

    def test_ai_reinstall_stops_on_unsupported_node_version(self):
        self.prepare_ai_migration()
        self.env["FAIL_NODE"] = "1"
        result = self.run_bootstrap("ai-reinstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Node.js 22.19", result.stderr)
        self.assertTrue(self.legacy_ai.exists())
        self.assertFalse(any(cmd[0] == "npm" for cmd in self.commands()))

    def test_ai_clean_preserves_unrelated_launchers_and_does_not_require_node(self):
        self.prepare_ai_migration()
        codex = self.root / ".local/bin/codex"
        codex.unlink()
        codex.write_text("unrelated executable")
        (self.bin / "node").unlink()
        self.env["CLAUDE_STATUS"] = "config-files"
        result = self.run_bootstrap("ai-clean")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(codex.read_text(), "unrelated executable")
        self.assertEqual((self.root / ".local/bin/claude").read_text(), "old manual launcher")
        self.assertFalse((self.root / ".local/bin/pi").is_symlink())
        self.assertFalse(self.legacy_ai.exists())
        self.assertFalse(any(cmd[0] == "apt-get" for cmd in self.commands()))
        for name in self.agent_data:
            self.assertEqual((self.root / name).read_text(), "private agent data")

    def test_ai_clean_refuses_to_remove_a_new_npm_prefix_inside_old_installations(self):
        self.prepare_ai_migration()
        result = self.run_bootstrap("ai-clean", f"AI_NPM_PREFIX={self.legacy_ai / 'npm'}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("it contains AI_NPM_PREFIX", result.stderr)
        self.assertTrue(self.legacy_ai.exists())
        self.assertTrue(self.claude_source.exists())
        self.assertEqual(self.commands(), [])

    def test_nfs_replaces_only_the_share_and_preserves_boot_configuration(self):
        self.write_tool("extrepo")
        for tool in ("systemctl", "findmnt", "mountpoint"):
            self.write_tool(tool)
        fstab = self.root / "fstab"
        original = "UUID=new-encrypted-root / ext4 defaults 0 1\nUUID=new-efi /boot/efi vfat umask=0077 0 1\n192.168.1.11:/srv/data /srv/data nfs defaults,auto 0 0\n"
        fstab.write_text(original)
        for _ in range(2):
            result = self.run_bootstrap("nfs-install", f"FSTAB={fstab}")
            self.assertEqual(result.returncode, 0, result.stderr)
        result_text = fstab.read_text()
        self.assertIn("UUID=new-encrypted-root / ext4 defaults 0 1", result_text)
        self.assertIn("UUID=new-efi /boot/efi vfat umask=0077 0 1", result_text)
        self.assertEqual(result_text.count("192.168.1.11:/srv/data"), 1)
        self.assertIn("nofail,_netdev,x-systemd.automount", result_text)
        self.assertEqual((self.root / "fstab.deps-backup").read_text(), original)

    def test_obsidian_check_detects_unsynced_plugins(self):
        vault = self.root / "vault/.obsidian"
        vault.mkdir(parents=True)
        expected = json.loads((self.root / "config/obsidian-plugins.json").read_text())
        (vault / "community-plugins.json").write_text(json.dumps(expected))
        result = self.run_bootstrap("obsidian-check", f"VAULT={vault.parent}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Plugins missing or disabled", result.stderr)
        for name in expected:
            plugin = vault / "plugins" / name
            plugin.mkdir(parents=True)
            (plugin / "manifest.json").write_text(json.dumps({"id": name}))
            (plugin / "main.js").write_text("")
        result = self.run_bootstrap("obsidian-check", f"VAULT={vault.parent}")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_steam_uses_matching_driver_and_ignores_transitional_package(self):
        self.env["NVIDIA_PACKAGES"] = (
            "libnvidia-gl-590\tamd64\tii \t595.99.02-0ubuntu0.26.04.1\n"
            "libnvidia-gl-595\tamd64\tii \t595.99.02-0ubuntu0.26.04.1\n"
            "libnvidia-gl-595\ti386\tii \t595.99.02-0ubuntu0.26.04.1\n"
        )
        result = self.run_bootstrap("steam-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [
            ["dpkg", "--add-architecture", "i386"],
            ["apt-get", "update"],
            ["apt-get", "install", "--yes", "--install-recommends", "steam-installer", "libnvidia-gl-595:i386"],
        ])

    def test_steam_requires_an_installed_driver_before_changing_anything(self):
        self.env["NVIDIA_PACKAGES"] = "libnvidia-gl-595\tamd64\tun \t\n"
        result = self.run_bootstrap("steam-install")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expected one installed NVIDIA graphics library", result.stderr)
        self.assertEqual(self.commands(), [])

    def test_steam_supports_nvidia_unversioned_library_packaging(self):
        self.env["NVIDIA_PACKAGES"] = "libnvidia-gl\tamd64\tii \t595.99.02-1\n"
        result = self.run_bootstrap("steam-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands()[-1][-1], "libnvidia-gl:i386")


if __name__ == "__main__":
    unittest.main()
