These are public repository signing keys and deb822 source declarations.
`make sources-install` substitutes the running Ubuntu codename for
`@UBUNTU_CODENAME@` and installs the keys and sources before APT refreshes.

Docker and HashiCorp use Ubuntu suites. Signal and 1Password use the vendors'
distribution-independent suites. Signal's `xenial` suite is the one currently
published by Signal for supported Debian-based systems, including Ubuntu.

| Key | Publisher URL | Primary fingerprint |
| --- | --- | --- |
| `docker.asc` | https://download.docker.com/linux/ubuntu/gpg | `9DC858229FC7DD38854AE2D88D81803C0EBFCD88` |
| `hashicorp.asc` | https://apt.releases.hashicorp.com/gpg | `D55C0D1AC78A8D8126CB631CFC9CA96ACA026560` |
| `1password-archive-keyring.gpg` | https://downloads.1password.com/linux/keys/1password.asc | `3FEF9748469ADBE15DA7CA80AC2D62742012EA22` |
| `signal-desktop-keyring.gpg` | https://updates.signal.org/desktop/apt/keys.asc | `DBA36B5181D0C816F630E889D980A17457F6FB06` |
| `claude-code.asc` | https://downloads.claude.ai/keys/claude-code.asc | `31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE` |

The `.gpg` files are dearmoured public keys. Signal's source file comes from
https://updates.signal.org/static/desktop/apt/signal-desktop.sources.

Signal and 1Password keep their publisher-standard source filenames and
`/usr/share/keyrings` locations. In particular, 1Password's package recreates
its own `1password.sources` file during installation. Matching that filename
and key path prevents a second source with conflicting `Signed-By` values.
The other manually managed keys live under `/etc/apt/keyrings`.

Claude Code uses Anthropic's signed `stable` APT repository, as documented in
https://code.claude.com/docs/en/setup#install-with-linux-package-managers.
Its release-signing fingerprint and current repository signature were verified
when adding the source. Updates follow APT rather than a separate npm runtime.

Review signing-key rotations against the publishers' current installation
instructions before replacing these public keys. Never add private keys or
authenticated repository URLs here.
