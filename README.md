# deps

Machine dependencies and selected personal configuration. Long-lived branches
include `ubuntu-laptop`, `mbp`, `m1`, `raspberry-pi` and `geekom-mini-air12`.
The targets below apply to the Ubuntu amd64 laptop branch.

Run targets from this directory. `make setup` performs the selected laptop
setup in order; targets are serialised to avoid concurrent APT operations.
It installs software and configuration but does not copy personal libraries,
change the NVIDIA driver, import SSH configuration or open applications.

| Target | What it does |
| --- | --- |
| `make setup` | APT packages, Nix daemon, Neovim, Kitty, shell, Git signing, NFS, selected apps, audiobook applications and the three AI CLIs. |
| `make install` | Install APT packages, Flatpak apps, AI CLIs, Tailscale and Meetily; record package inventories. |
| `make apt-install` | Configure external sources, refresh APT and install `aptfile.txt`; record the APT inventory. |
| `make repos` | Install public fallback keys/source files, ensure extrepo is installed, enable `apt-repos.txt` and refresh APT. |
| `make dotfiles` | Use GNU Stow to link all five user configuration packages and include the Git settings; no package installation or service changes. |
| `make nix-install` | Retain an active Nix daemon, or install Ubuntu's Nix packages if absent and enable the daemon socket; install direnv and enable flakes in the user config. |
| `make nvim-install` | Install Neovim, your `init.lua`, and the two plugins pinned in `config/nvim/plugins.txt`. |
| `make kitty-install` | Install Kitty and the three active settings from your existing configuration. |
| `make shell-install` | Install Zsh, pinned Oh My Zsh, syntax highlighting, the bundled `z` plugin, clipboard integration and direnv; select Zsh as the login shell. |
| `make git-install` | Install Git/GitHub CLI/1Password and include your Git identity and SSH signing settings. |
| `make nfs-install` | Back up fstab, replace only the `/srv/data` entry, and arrange a network automount. |
| `make books-install` | Pinned, SHA256-checked Libation and OpenAudible publisher packages. |
| `make flatpak-install` | Install the apps in `flatpakfile.txt` from Flathub and record the inventory. |
| `make ai-install` | Install/update Codex, pi and Claude Code using the Node.js/npm toolchain on PATH. |
| `make ai-check` | Show the executable paths and versions of Codex, pi and Claude Code; no login or model requests. |
| `make steam-install` | Detect the installed NVIDIA graphics-library package and install its matching i386 package, Steam and recommended dependencies. |
| `make tailscale-install` | Install Tailscale through extrepo/APT and enable its daemon; prints the command for account login. |
| `make meetily-build` | Build pinned Meetily Community Edition into a Debian package with Vulkan acceleration. |
| `make meetily-install` | Build Meetily and install its Debian package through APT; included in `make install` and `make setup`. |

Tailscale is declared in `apt-repos.txt` and `aptfile.txt`, using the existing
extrepo machinery for its source and signing key. Run `make tailscale-install`,
then `sudo tailscale up` to authenticate this machine to your tailnet. Login
is interactive and is separate from machine setup. The local extrepo Trixie
catalogue supplies Tailscale's Debian Trixie stable repository.

Meetily Community Edition is built from the [official source](https://github.com/Zackriya-Solutions/meetily)
using the revision and pnpm version in `config/meetily.mk`. Node.js/npm and
Rust must be available (`make toolchains` supplies them). APT build dependencies
are in `aptfile.txt`; frontend installation uses the frozen pnpm lockfile and
Rust builds use `--locked`. Source/build output lives under
`~/.local/share/deps/meetily`, and the dedicated pnpm installation under
`~/.local/share/deps/meetily-tools`. Neither is stored in this repository.
Override `MEETILY_DIR` or `MEETILY_TOOLS` to relocate them.

Run `make meetily-install` to build and install the desktop app. Vulkan is the
default for this laptop; `make meetily-install MEETILY_GPU=cpu` builds without
GPU features. `MEETILY_GPU=cuda` requires a compatible CUDA toolkit installed
separately. The build downloads npm/Cargo dependencies and upstream build-time
assets, including FFmpeg. The Debian package is under
`$(MEETILY_DIR)/target/release/bundle/deb/`. Local builds disable updater
artifact signing; rebuild through this repo to update. Models and recording
setup are configured in Meetily after launch. A completed build and a desktop
recording smoke test are still required to validate it on Ubuntu 26.04.

User configuration lives in `stow/` and is linked into place using GNU Stow.
`stow` is listed in `aptfile.txt`, or install it yourself before linking:

```sh
sudo apt install stow
make dotfiles
```

The `nvim`, `kitty`, `nix` and `git` packages target `XDG_CONFIG_HOME` (default
`~/.config`); `shell` targets your home directory. Individual installation
targets link just their own package. Existing files, including copies from
the earlier bootstrap, are moved to numbered `.deps-backup` backups before
linking. Reruns preserve correct links. Existing symlinks for whole application
directories are left for you to resolve rather than modifying another checkout.
Stow uses `--no-folding` to link individual files, keeping generated data such
as downloaded Neovim plugins outside this repo.

Keep this checkout at a stable path: the live configs point into it. Edits
through either path change the Git-tracked file, and pulling changes updates
the active configuration. Auxiliary declarations, such as plugin pins and the
NFS entry, remain in `config/`.

Git settings are included from `~/.config/git/deps.config`, preserving the
existing global config and adding the include only once. Only the public SSH
signing key is committed. Sign in to 1Password and enable its SSH agent on the
new laptop. The existing migrated SSH configuration is left alone.

Nix remains a daemon plus flakes/direnv workflow. On installations with a
`nix-users` group, `nix-install` adds the current user to it for daemon socket
access. Reboot after a new group membership is added to refresh all sessions.
No global profiles, channels,
old language-runtime directories or Nix store are migrated. An existing Nix
installation is retained, so this target does not install a second Nix over
an upstream installation. LSP executables referenced by Neovim (`deno`,
`terraform-ls`, `bash-language-server`, `nil`) should be supplied by each
project's flake. The same applies to language-based tools such as `audiblez`.

AI tools use your existing Node.js/npm toolchain (Node.js 22.19 or newer).
Local inference uses the APT packages `llama.cpp-tools` and
`libggml0-backend-vulkan` in `aptfile.txt`. Run `llama-cli --list-devices`
to identify the NVIDIA device before starting the server. On this laptop,
`Vulkan0` is Intel graphics and `Vulkan1` is the RTX 5070. Device numbering
may change; select the device reported on the current machine.

For pi's built-in llama.cpp integration, create `~/models` and run:

```sh
mkdir -p ~/models
llama-server --models-dir ~/models --no-models-autoload --jinja \
  --device Vulkan1 -ngl 999 -c 8192 --host 127.0.0.1 --port 8080
```

In pi, use `/login llama.cpp` with `http://127.0.0.1:8080`, then `/llama`
to download/load a GGUF model and `/model` to select it. Model weights stay
outside Git. Context size and model size must fit available memory.
GPU access is required: an agent sandbox that hides GPU devices will report
no Vulkan devices even when the host driver works.

Vulkan inference was verified on the RTX 5070 with Ubuntu's llama.cpp build
8681 and `Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M`. This small model is a
hardware smoke test, not a recommended coding model. The verification command is:

```sh
llama-cli -hf Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M \
  --device Vulkan1 -ngl 999 -c 2048 -n 32 --single-turn \
  --verbosity 4 -p 'Reply with one short sentence: what is 2 plus 2?'
```

Check the logs for layers offloaded to GPU, model buffers on `Vulkan1`, and
successful generation. The first run downloads weights into llama.cpp's cache.

Qwen3.8-27B `UD-Q4_K_M` was also tested with an 8192-token context. Ubuntu's
build 8681 cannot load its MTP prediction-head tensors (`missing tensor
'blk.64.ssm_conv1d.weight'`); overriding the block count also fails. This
model needs a newer runtime. A temporary official upstream Vulkan build
b11669 (v0.7.0, commit `620d2225c`) loaded it without overrides, offloading
24/66 reported layers and about 5977 MiB of weights to the RTX 5070, with
about 9380 MiB of weights in host RAM. The initial short test measured
4.4 prompt tokens/s and 2.8 generated tokens/s using the default three CPU
threads. This is a short-prompt result, not a coding-agent benchmark.
Repeating with `-t 8 -tb 8` measured 20.2 prompt tokens/s and 4.0 generated
tokens/s; use eight threads as the starting point for this laptop.
The APT installation remains in place; the newer test runtime is under
`/tmp/llama-b11669` and is not a persistent installation.

AI targets use Node.js/npm on PATH, or load NVM from `NVM_DIR` (default
`~/.nvm`) when they are missing. `make toolchains` installs uv, Rust, NVM and
Node.js 24 LTS (Krypton), sets it as the default Node version, and adds NVM startup hooks to
Bash and Zsh. Open a new terminal afterwards to load it in your shell.
To install or update only the AI tools, run:

```sh
make ai-install
rehash
make ai-check
```

For a fresh install or later updates, use `make ai-install`. `ai-tools.txt`
contains one official npm package per line with optional blank lines and
full-line comments. The default `@latest` tags can be replaced with exact
versions. Packages are installed with `npm install --global --include=optional`
into the user-owned `~/.local` prefix; no `sudo npm` or persistent npm config
changes are used. Set `AI_NPM_PREFIX` to use a different prefix and add its
`bin` directory to PATH. Keep your Node toolchain available for the npm launchers.

Existing non-npm launchers receive `.deps-backup` backups; if npm fails,
those launchers are restored. `make ai-check` reports executable paths and
versions; check interactive startup and session resumption separately.

Start `codex`, `pi` and `claude` normally; existing agent data stays in place.
MCP consolidation belongs in your separate repo. See the [official OpenAI documentation](https://developers.openai.com/codex/cli/),
[pi's upstream docs](https://github.com/earendil-works/pi/tree/main/packages/coding-agent)
and [Claude Code setup](https://code.claude.com/docs/en/setup).

An already-active `nix-daemon.service` is retained without starting its socket
again. This supports an existing daemon that owns its listening socket itself;
direnv installation and the user configuration link still run. If the daemon
is inactive, the target enables and starts `nix-daemon.socket` as before.

If you configured Kitty on the new laptop before using this repo, compare the
saved `kitty.conf.deps-backup` with `stow/kitty/kitty/kitty.conf` and keep the
settings you want in the tracked file. It currently contains only font size
12 and the remote-control socket settings. Edits to the linked live file also
edit the repository file. Kitty's application installation and its config
are separate; its [configuration documentation](https://sw.kovidgoyal.net/kitty/conf/)
describes the configuration search paths.

The shell files have different roles:

| File | Role and migration choice |
| --- | --- |
| `.zshrc` | Interactive Zsh setup: Oh My Zsh/theme/plugins, aliases and direnv. This is the file installed here. |
| `.zshenv` | Runs for every Zsh invocation, including scripts. The old one loads Cargo; it is left to your flake workflow. |
| `.zlogin` | Runs for login Zsh sessions. The old one loads RVM; it is left to your flake workflow. |
| `.profile` | General login environment used by some shells/sessions. Preserve the new machine's defaults. |
| `.bash_profile` | Bash login setup; the old file mostly loads `.profile` and legacy runtimes. It is not migrated. |

Oh My Zsh supplies the existing `mh` theme, Git shortcuts and the `z` directory
navigation plugin. No separate `~/Projects/util/z` checkout is needed.
Navigation history is optional and not copied. The GDrive function and old
pyenv/NVM/RVM/Deno startup hooks are omitted. `clip` uses `wl-copy` on Wayland
and `xclip` on X11. Start a new terminal after `shell-install`.

The NFS entry is in `config/system/fstab.nfs`. The target preserves the new
laptop's root, EFI and swap entries, backs up the old fstab, verifies the result
and uses `nofail` plus systemd automount so the laptop can boot away from the
home network. It does not change user IDs, group IDs or server ownership.
The old laptop uses UID 1001 and a `mediaadmin` group: check server permissions
if the new account uses different numeric IDs.

`steam-install` expects an NVIDIA graphics stack already installed. It accepts
Ubuntu's versioned `libnvidia-gl-<branch>` packages and NVIDIA's unversioned
`libnvidia-gl`, ignores uninstalled/unknown records and transitional branches,
and stops if it cannot identify one installed native graphics library. It
then enables i386, refreshes APT and explicitly installs recommendations.
It does not install or switch a kernel driver. Ubuntu's package names differ
from Debian's `nvidia-driver-libs:i386`.

The laptop's RTX 5070 uses TUXEDO's NVIDIA 580.178.04 open driver and
unversioned library packages; driver access and Vulkan inference were verified.
Use `nvidia-smi` and `dpkg -l | grep -Ei 'nvidia|libnvidia'` to inspect the
installed stack after upgrades. A `un` entry in `dpkg-query` means the package
is not installed, so it cannot identify the active driver. See Ubuntu's
[Steam GPU instructions](https://ubuntu.com/docs/steam/howto/dedicated-gpu/).
The optional `make steam-install` target stops before making changes if its
detection is inconclusive; it is separate from `make setup` and still needs
validation on this laptop.

Obsidian vaults and plugins are supplied by sync. On each device, enable both
**Active community plugin list** and **Installed community plugin list** in
Obsidian Sync's vault configuration settings. After syncing, check:

```sh
make obsidian-check VAULT="$HOME/obsidian"
make obsidian-check VAULT="$HOME/Projects/obsidian-gtd" OBSIDIAN_PLUGINS=config/obsidian-gtd-plugins.json
```

This checks the selected vault's enabled plugin IDs and downloaded plugin
files. It does not change vault contents or copy plugin credentials into Git.
The expected personal-vault and GTD-vault plugin lists are stored separately.
Brave profile transfer/pairing is handled separately; this repo installs the
native browser. Signal uses its official signed APT source; its old Flatpak
entry has been removed. Existing Flatpak installations are not uninstalled.

Books and audiobook files stay outside Git. After setup, run these on the new
laptop, substituting the old laptop's SSH name:

```sh
make libraries-plan LIBRARY_SOURCE=oscar@old-laptop:/home/oscar
make libraries-copy LIBRARY_SOURCE=oscar@old-laptop:/home/oscar
```

The first target previews the transfer. The second uses rsync over SSH, copies
only `config/library-paths.txt`, keeps destination ownership with the current
user, and backs up overwritten files under `~/.local/share/deps/library-backups`.
It does not delete destination files. The selection includes Calibre's library
and both native and Flatpak plugin/settings directories, OpenAudible's
library/settings, Libation's
settings/database and `Documents/Libation` books. Those app directories may
contain credentials; they are transferred privately and never committed here.
Close the library applications while copying their databases. Reopen them on
the new laptop and select the transferred library paths; vendor sign-in or
license activation may still be needed. `book-debs.txt` records publisher
release URLs and SHA256 hashes, which must be reviewed together when updating.

Verified publisher packages are cached under `~/.cache/deps/debs`, then copied
to a temporary directory in `/tmp` with directory mode 0755 and file mode 0644
for APT to read as `_apt`. The temporary copies are removed on success or
failure. This avoids the unsandboxed-download notice when the home/cache path
is private, without changing home-directory permissions or disabling APT's
sandbox. That notice alone does not mean installation failed; check with
`dpkg-query -W -f='${Status}\n' openaudible` if needed.

`aptfile.txt` declares APT packages; `apt-repos.txt` declares extrepo catalogue
identifiers. Both accept one name per line, leading/trailing whitespace, blank
lines and full-line comments starting with `#`. Inline comments are not used.
`extrepo search TERM` discovers identifiers. Declared entries are enabled every
run, restoring disabled extrepo sources after upgrades. `enable` preserves
existing metadata; use `sudo extrepo update NAME` when its key/URL needs a
reviewed refresh. A failed enable stops the bootstrap.

Ubuntu's extrepo 0.15 defaults to Debian's Trixie catalogue. The selected
Proton VPN, Yarn and Brave entries use distribution-independent vendor suites.
Signal and 1Password source declarations and public keys live in `sources/`,
using publisher-standard filenames and key paths. See `sources/README.md` for provenance.
Before first adopting extrepo, retire overlapping vendor Proton/Yarn/Brave sources
so APT does not see conflicting signing-key paths. A source disabled by an
Ubuntu upgrade is restored by the appropriate target on the next run.

`aptfile.txt` is the shared list for ordinary APT packages. Individual
configuration targets depend on `apt-install`, so they install that full list.
Nix bootstrap packages, detected Steam graphics libraries and downloaded book
packages retain their conditional installation logic. `make install` installs
software; `make setup` additionally applies configuration and special setup.

`flatpakfile.txt` is the shared app list, including Obsidian, Calibre, VLC and
GIMP. `make install` includes `flatpak-install`; `flatpak-update` updates all
system Flatpaks. Existing APT copies of overlapping apps are not removed.

The tracked manifests are historical snapshots for investigation. APT's
snapshot includes available packages as well as installed status; it does not
pin versions or act as a reproducible lockfile. Install/update targets refresh
them, and `make manifest` refreshes both explicitly.
Package removal stays a separate explicit `make autoremove` operation.
