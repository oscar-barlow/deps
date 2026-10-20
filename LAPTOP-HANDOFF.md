# Continue on the new laptop

The laptop configuration and extrepo bootstrap are merged into `ubuntu-laptop`.
Update that branch in your existing clone, keeping the checkout at its stable
path for Stow:

```sh
git fetch origin
git switch ubuntu-laptop
git pull --ff-only
```

Read the target table in [README.md](README.md). `make setup` runs the selected
software/configuration targets in order; each can also be run individually.
User configs are linked from `stow/` using GNU Stow; keep the checkout at a
stable path. Existing config files and fstab are backed up. To apply only the
config links after installing Stow yourself, run `make dotfiles`; this does
not install applications or alter services. The user has run setup on the new
laptop and merged the Nix-daemon and APT staging fixes.

The user reports Zsh, Oh My Zsh, Nix and direnv are all looking fine on the
new laptop. SSH configuration was also handled separately. Focus the remaining
checks on AI tool installation, Neovim, Kitty, GPU libraries and personal data.

## Install the three AI tools

AI tools now use the official npm packages. Activate Node.js/npm (Node.js
22.19+) and run `make ai-install` followed by `make ai-check`. `make install`
also includes AI installation. Existing configuration and sessions stay in
place; verify interactive startup and resume locally. The one-time AI cleanup
and reinstall targets have been retired. MCP configuration belongs in the
separate repository.

## Neovim and Kitty

Open Neovim on a file in a project whose flake supplies its language server.
Check the UI, `:DiffviewOpen` and `gd` after the server attaches. The two plugins
are installed by `make nvim-install`; language tools remain project-specific.

Kitty was already configured on the new laptop using its website instructions.
Use these commands there to identify the active installation and config:

```sh
type -a kitty
readlink -f "${XDG_CONFIG_HOME:-$HOME/.config}/kitty/kitty.conf"
ls -l "${XDG_CONFIG_HOME:-$HOME/.config}/kitty"
```

Compare the saved `kitty.conf.deps-backup` (or numbered backup) with the active
config. Keep the desired settings in `stow/kitty/kitty/kitty.conf`; editing
the live Stow link edits that tracked file. It currently contains only font
size 12 and remote-control socket settings. No new-laptop Kitty config has
been inspected from the old laptop. Check for a website installation shadowing
APT's `/usr/bin/kitty` before removing either installation.

## NVIDIA and Steam: finish here

The new laptop has an NVIDIA RTX 5070. We have not confirmed its installed
driver version or package layout. The earlier narrow `dpkg-query` showed `un`
records; those are not installed packages and cannot identify the driver.
`nvidia-smi` and the broader package listing produced output on the new laptop,
but that output has not been inspected here. No output needs carrying back to
the old laptop: inspect it locally in the resumed session.

```sh
nvidia-smi
dpkg -l | grep -Ei 'nvidia|libnvidia'
```

Ubuntu usually calls the 32-bit OpenGL package
`libnvidia-gl-<installed-driver-branch>:i386`, whereas the originally suggested
`nvidia-driver-libs:i386` is a Debian package name. Match the installed package
family and version rather than guessing a branch. See the linked Ubuntu
instructions in the README.

`make steam-install` is optional and separate from `make setup`. It attempts
to match one installed amd64 NVIDIA graphics-library package, enables i386,
refreshes APT, then installs Steam and that package's i386 counterpart with
recommended dependencies. It stops without system changes if detection is
ambiguous or finds nothing. Actual hardware validation remains to do. Review the
APT transaction on the new machine before relying on this target with its
vendor driver packaging. Kernel/driver replacement is outside this target.

## Remaining personal steps

- Sign in to 1Password, enable its SSH agent/signing integration, and authenticate
  GitHub CLI. SSH configuration has already been migrated separately.
- Connect Obsidian Sync and enable both active and installed community plugin
  lists on this device. Run the vault checks from the README after syncing.
- Transfer Brave data separately using your chosen pairing/transfer method.
- Check NFS numeric ownership: the old account uses UID 1001. Do not copy the
  old root/EFI entries or change server ownership to make IDs match.
- Preview and then copy Calibre/Libation/OpenAudible libraries with
  `libraries-plan` and `libraries-copy`; keep their databases closed during
  transfer. Settings can contain credentials and stay outside Git.

Check NFS access on the home network with `id` and `ls /srv/data/`. This
triggers the automount; confirm the intended read/write access before changing
any ownership. For book transfers, close Calibre/Libation/OpenAudible, replace
`old-laptop` with a reachable SSH name or IP, and run:

```sh
make libraries-plan LIBRARY_SOURCE=oscar@old-laptop:/home/oscar
make libraries-copy LIBRARY_SOURCE=oscar@old-laptop:/home/oscar
```

After Obsidian sync completes, run the appropriate vault checks from README.md.
Library files and app databases remain outside Git; browser transfer is manual.

Deferred: VS Code/Cursor and whisper-talk
are for later. `Documents/ProStudioMasters/YUNGBLUD` and the two small Meetily
recording directories have not been selected for transfer. GDrive, language
runtime directories, container databases, browser/Signal/Proton indexes and
other unselected machine data are not part of this migration.
