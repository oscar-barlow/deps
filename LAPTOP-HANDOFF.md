# Continue on the new laptop

This work is on `feat/laptop-config`, based on `ubuntu-laptop` with the merged
extrepo bootstrap. Fetch and check out the branch in your existing clone:

```sh
git fetch origin
git switch feat/laptop-config
make check
```

Read the target table in [README.md](README.md). `make setup` runs the selected
software/configuration targets in order; each can also be run individually.
User configs are linked from `stow/` using GNU Stow; keep the checkout at a
stable path. Existing config files and fstab are backed up. To apply only the
config links after installing Stow yourself, run `make dotfiles`; this does
not install applications or alter services. This branch
has been tested with temporary directories and mocked privileged commands;
the installation targets have not been run on either laptop during preparation.

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
ambiguous or finds nothing. Tests cover versioned, transitional, unversioned
and uninstalled records; actual hardware validation remains to do. Review the
APT transaction on the new machine before relying on this target with its
vendor driver packaging. Kernel/driver replacement is outside this target.

## Remaining personal steps

- Sign in to 1Password, enable its SSH agent/signing integration, and authenticate
  GitHub CLI. SSH configuration has already been migrated separately.
- Start a new terminal after `shell-install`. Oh My Zsh includes the `z` plugin;
  its history is optional. Project flakes supply language tools through direnv.
- Connect Obsidian Sync and enable both active and installed community plugin
  lists on this device. Run the vault checks from the README after syncing.
- Transfer Brave data separately using your chosen pairing/transfer method.
- Check NFS numeric ownership: the old account uses UID 1001. Do not copy the
  old root/EFI entries or change server ownership to make IDs match.
- Preview and then copy Calibre/Libation/OpenAudible libraries with
  `libraries-plan` and `libraries-copy`; keep their databases closed during
  transfer. Settings can contain credentials and stay outside Git.

Deferred: AI/Codex/Claude setup needs discussion. VS Code/Cursor and whisper-talk
are for later. `Documents/ProStudioMasters/YUNGBLUD` and the two small Meetily
recording directories have not been selected for transfer. GDrive, language
runtime directories, container databases, browser/Signal/Proton indexes and
other unselected machine data are not part of this migration.
