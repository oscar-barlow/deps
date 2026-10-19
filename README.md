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
| `make setup` | APT packages, Nix daemon, Neovim, Kitty, shell, Git signing, NFS, selected apps and audiobook applications. |
| `make install` | Configure external sources, refresh APT and install `aptfile.txt`; record the package inventory. |
| `make repos` | Install public fallback keys/source files, ensure extrepo is installed, enable `apt-repos.txt` and refresh APT. |
| `make nix-install` | Install Ubuntu's `nix-bin`/`nix-setup-systemd` if Nix is absent, enable its daemon socket, install direnv and enable flakes in the user config. |
| `make nvim-install` | Install Neovim, your `init.lua`, and the two plugins pinned in `config/nvim/plugins.txt`. |
| `make kitty-install` | Install Kitty and the three active settings from your existing configuration. |
| `make shell-install` | Install Zsh, pinned Oh My Zsh, syntax highlighting, the bundled `z` plugin, clipboard integration and direnv; select Zsh as the login shell. |
| `make git-install` | Install Git/GitHub CLI/1Password and include your Git identity and SSH signing settings. |
| `make nfs-install` | Back up fstab, replace only the `/srv/data` entry, and arrange a network automount. |
| `make apps-install` | Native Brave and Signal; Obsidian from Flathub. |
| `make books-install` | Calibre from Flathub; pinned, SHA256-checked Libation and OpenAudible publisher packages. |
| `make steam-install` | Detect the installed NVIDIA graphics-library package and install its matching i386 package, Steam and recommended dependencies. |
| `make check` | Tests using temporary files and mocked privileged commands; no system setup. |

User configuration is copied from `config/`. Existing differing files receive
numbered `.deps-backup` backups; unchanged files are left alone. Git settings
are included from `~/.config/git/deps.config`, preserving the existing global
config and adding the include only once. Only the public SSH signing key is
committed. Sign in to 1Password and enable its SSH agent on the new laptop.
The existing migrated SSH configuration is left alone.

Nix remains a daemon plus flakes/direnv workflow. No global profiles, channels,
old language-runtime directories or Nix store are migrated. An existing Nix
installation is retained, so this target does not install a second Nix over
an upstream installation. LSP executables referenced by Neovim (`deno`,
`terraform-ls`, `bash-language-server`, `nil`) should be supplied by each
project's flake. The same applies to language-based tools such as `audiblez`.

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

Finish NVIDIA setup on the new laptop. Its driver version and package layout
have not yet been confirmed; do not choose a driver branch from the RTX 5070
model alone. Use `nvidia-smi` and `dpkg -l | grep -Ei 'nvidia|libnvidia'` there
to inspect the installed stack. A `un` entry in `dpkg-query` means the package
is not installed, so it cannot identify the active driver. See Ubuntu's
[Steam GPU instructions](https://ubuntu.com/docs/steam/howto/dedicated-gpu/).
The optional `make steam-install` target stops before making changes if its
detection is inconclusive; it is separate from `make setup` and still needs
validation on the new laptop. There is no need to relay diagnostic output
back to the old laptop. See [LAPTOP-HANDOFF.md](LAPTOP-HANDOFF.md) to resume.

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

`aptfile.txt` declares APT packages; `apt-repos.txt` declares extrepo catalogue
identifiers. Both accept one name per line, leading/trailing whitespace, blank
lines and full-line comments starting with `#`. Inline comments are not used.
`extrepo search TERM` discovers identifiers. Declared entries are enabled every
run, restoring disabled extrepo sources after upgrades. `enable` preserves
existing metadata; use `sudo extrepo update NAME` when its key/URL needs a
reviewed refresh. A failed enable stops the bootstrap.

Ubuntu's extrepo 0.15 defaults to Debian's Trixie catalogue. The selected
Proton VPN, Yarn and Brave entries use distribution-independent vendor suites.
Docker/HashiCorp need Ubuntu-specific sources; their reviewed declarations and
public keys live in `sources/`. Signal and 1Password use publisher-standard
filenames/key paths there too. See `sources/README.md` for provenance.
Before first adopting extrepo, retire overlapping vendor Proton/Yarn sources
so APT does not see conflicting signing-key paths. A source disabled by an
Ubuntu upgrade is restored by the appropriate target on the next run.

`make flatpak-install` installs the broader existing `flatpakfile.txt` list;
`apps-install` and `books-install` install only the selected applications.
Package removal stays a separate explicit `make autoremove` operation.
