# deps
A repository with many long-lived branches, which defines the dependencies that live on my various machines. These take the form of:
* `Brewfile` and associated lockfile
* A `txt` file with apt dependencies in it, and a `Makefile` with convenience commands
* Same deal, but a snapfile, sigh

The machines currently supported by this repo are:
* A Macbook Pro, mostly for work (`mbp`)
* A personal laptop running Ubuntu (`ubuntu-laptop`)
* A Raspberry Pi (`raspberry-pi`)

On the `ubuntu-laptop` branch, `aptfile.txt` declares packages and
`apt-repos.txt` declares third-party repositories managed by `extrepo`.
Both files contain one name per line. Leading and trailing whitespace is
trimmed; blank lines and lines whose first non-whitespace character is `#`
are ignored. Inline comments are not supported.

Run `make install` from this directory. Its Makefile recipe uses Bash strict
mode and:

1. Reads both lists before making changes.
2. If `extrepo` is missing, refreshes APT's indexes and installs it from Ubuntu
   Universe.
3. Runs `sudo extrepo enable NAME` for every declared repository, every time.
4. Refreshes APT's indexes after repository configuration.
5. Installs the packages declared in `aptfile.txt`.

When adopting `extrepo` on an existing machine, retire any overlapping vendor
`.list` or `.sources` entries once, retaining backups outside APT's active file
extensions. On the current laptop these are `protonvpn-stable.sources`
(already disabled) and `yarn.sources` under `/etc/apt/sources.list.d/`.
Otherwise duplicate sources can conflict over `Signed-By`. The bootstrap does
not automatically rewrite vendor-owned files; subsequent runs manage the
`extrepo_*.sources` files created by `extrepo`.

After successful installation, Make records the existing APT manifest. Package
removal is a separate, explicit `make autoremove` operation.

Rerunning `make install` is expected, including after an Ubuntu release upgrade
disables third-party repositories. In `extrepo` 0.15, enabling an existing
repository sets `Enabled: yes` even if it is already enabled. It does not
refresh the existing URL, suite or signing key; use `sudo extrepo update NAME`
when those need updating. A failed enable stops the bootstrap before the final
APT refresh and package installation.

Discover catalogue identifiers with `extrepo search TERM`, for example
`extrepo search proton` or `extrepo search yarn`. The verified identifiers are
`protonvpn` and `yarnpkg`, even though the Yarn package is named `yarn`.
The online catalogue is signature-checked by `extrepo`; the bootstrap uses its
normal configuration and does not bypass signature or licensing checks.

This first change manages Proton VPN and Yarn. A complete fresh-machine install
still needs the other external sources below. Ubuntu 26.04's `extrepo` 0.15
ships with `dist: debian`, `version: trixie` and only the `main` licensing policy
enabled. A catalogue entry's presence does not imply an Ubuntu-compatible
source. Check the source and policy printed by `extrepo search` before adding
an entry to `apt-repos.txt`.

| Existing software | Catalogue entry | Remaining setup |
| --- | --- | --- |
| Proton VPN | `protonvpn` | Declared; uses the vendor's distribution-independent `stable` source. |
| Yarn | `yarnpkg` | Declared; uses the vendor's distribution-independent `stable` source. |
| Docker CE | `docker-ce` | Needs an Ubuntu `.sources` fallback: the default catalogue entry selects Debian Trixie. |
| Terraform | `hashicorp` | Needs an Ubuntu `.sources` fallback: the default entry selects Trixie and requires the `non-free` policy. |
| 1Password and CLI | `1password` | Catalogue-supported, but requires the `non-free` policy, which this bootstrap leaves unchanged. Its initial enable also installs the desktop app through catalogue post-enable commands. Review that policy and behaviour before declaring it, or use a `.sources` fallback. |
| TUXEDO support software | No entry found | Needs a vendor `.sources` fallback if the laptop's factory setup has not already configured it. |

TODO: add a small `sources/` fallback containing reviewed deb822 `.sources`
files and their public signing keys. Install the keys under `/etc/apt/keyrings`
and reference each key with that source's `Signed-By`. Ubuntu-specific suites
must match the running release. This change does not copy fallback files,
rewrite existing vendor sources, or enable Debian Docker/HashiCorp sources on
Ubuntu. Packages already installed without an active source do not demonstrate
that a fresh-machine bootstrap is complete.

Catalogue entries were checked against the
[signed Trixie index](https://extrepo-team.pages.debian.net/extrepo-data/debian/trixie/index.yaml)
using the keyring shipped in Ubuntu's `extrepo` 0.15 package. Recheck with
`extrepo search` when changing the list; catalogue contents can change.

Run `make check` for lightweight tests of the actual Makefile recipe. The
tests use temporary package lists and mocked commands; they do not use sudo,
install packages or change system repositories.
