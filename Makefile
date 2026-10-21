SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:
.NOTPARALLEL:
.DEFAULT_GOAL := install

CONFIG_HOME ?= $(or $(XDG_CONFIG_HOME),$(HOME)/.config)
DATA_HOME ?= $(or $(XDG_DATA_HOME),$(HOME)/.local/share)
CACHE_HOME ?= $(or $(XDG_CACHE_HOME),$(HOME)/.cache)
AI_NPM_PREFIX ?= $(HOME)/.local
APT_SOURCE_DIR ?= /etc/apt/sources.list.d
APT_KEY_DIR ?= /etc/apt/keyrings
VENDOR_KEY_DIR ?= /usr/share/keyrings
FSTAB ?= /etc/fstab
VAULT ?=
OBSIDIAN_PLUGINS ?= config/obsidian-plugins.json
LIBRARY_SOURCE ?=
MEETILY_DIR ?= $(DATA_HOME)/deps/meetily
MEETILY_TOOLS ?= $(DATA_HOME)/deps/meetily-tools
MEETILY_GPU ?= vulkan
MEETILY_FORCE ?= 0
include config/meetily.mk

define helpers
load_node() {
    if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
        export NVM_DIR="$${NVM_DIR:-$$HOME/.nvm}"
        if [[ -s $$NVM_DIR/nvm.sh ]]; then . "$$NVM_DIR/nvm.sh"; fi
    fi
}
read_list() {
    local entry
    entries=()
    while IFS= read -r entry || [[ -n $$entry ]]; do
        entry="$${entry#"$${entry%%[![:space:]]*}"}"
        entry="$${entry%"$${entry##*[![:space:]]}"}"
        [[ -z $$entry || $$entry == \#* ]] && continue
        entries+=("$$entry")
    done < "$$1"
}
stow_config() {
    local package=$$1 root=$$2 source target parent
    command -v stow >/dev/null 2>&1 || { printf 'Install GNU Stow first: sudo apt install stow\n' >&2; return 1; }
    install -d "$$root"
    root="$$(cd "$$root" && pwd -P)"
    shopt -s dotglob globstar nullglob
    for source in "$(CURDIR)/stow/$$package"/**; do
        [[ -f $$source || -L $$source ]] || continue
        target="$$root/$${source#"$(CURDIR)/stow/$$package/"}"
        parent=$${target%/*}
        while [[ $$parent != "$$root" ]]; do
            [[ ! -L $$parent ]] || { printf 'Config directory is already a symlink: %s\n' "$$parent" >&2; return 1; }
            parent=$${parent%/*}
        done
        if [[ -L $$target && $$target -ef $$source ]]; then continue; fi
        if [[ -e $$target || -L $$target ]]; then
            [[ ! -d $$target || -L $$target ]] || { printf 'Expected a config file: %s\n' "$$target" >&2; return 1; }
            mv -T --backup=numbered -- "$$target" "$$target.deps-backup"
        fi
    done
    stow --dir="$(CURDIR)/stow" --target="$$root" --no-folding --restow "$$package"
}
include_git_config() {
    if ! git config --global --get-all include.path | grep -Fxq "$(CONFIG_HOME)/git/deps.config"; then
        if [[ -e "$(HOME)/.gitconfig" ]]; then cp -a --backup=numbered "$(HOME)/.gitconfig" "$(HOME)/.gitconfig.deps-backup"; fi
        git config --global --add include.path "$(CONFIG_HOME)/git/deps.config"
    fi
}
checkout() {
    local target=$$1 url=$$2 revision=$$3
    if [[ -e $$target && ! -d $$target/.git ]]; then
        printf 'Not a managed Git checkout: %s\n' "$$target" >&2
        return 1
    fi
    [[ -d $$target/.git ]] || git init --quiet "$$target"
    if [[ "$$(git -C "$$target" rev-parse --verify HEAD 2>/dev/null || true)" != "$$revision" ]]; then
        git -C "$$target" fetch --quiet --depth=1 "$$url" "$$revision"
        git -C "$$target" checkout --quiet --detach "$$revision"
    fi
}
endef

.PHONY: setup
setup: install nix-install nvim-install kitty-install shell-install git-install nfs-install books-install

.PHONY: dotfiles
dotfiles:
	@$(helpers)
	stow_config nvim "$(CONFIG_HOME)"
	stow_config kitty "$(CONFIG_HOME)"
	stow_config nix "$(CONFIG_HOME)"
	stow_config git "$(CONFIG_HOME)"
	include_git_config
	stow_config shell "$(HOME)"

.PHONY: preflight
preflight:
	@for file in aptfile.txt apt-repos.txt; do
	    [[ -r $$file ]] || { printf 'Cannot read %s\n' "$$file" >&2; exit 1; }
	done
	if grep -Eq '^[[:space:]]*steam(-installer)?[[:space:]]*$$' aptfile.txt; then sudo dpkg --add-architecture i386; fi

.PHONY: install
install: apt-install flatpak-install ai-install tailscale-install meetily-install

.PHONY: apt-install
apt-install: preflight repos
	@$(helpers)
	read_list aptfile.txt
	packages=("$${entries[@]}")
	if (($${#packages[@]})); then
	    sudo apt-get install --yes -- "$${packages[@]}"
	fi
	apt list > aptfile.manifest

.PHONY: sources-install
sources-install:
	@source /etc/os-release
	[[ $$ID == ubuntu && $$(dpkg --print-architecture) == amd64 ]] || { printf 'This setup expects Ubuntu amd64.\n' >&2; exit 1; }
	sudo install -d -m 0755 "$(APT_SOURCE_DIR)" "$(APT_KEY_DIR)" "$(VENDOR_KEY_DIR)"
	shopt -s nullglob
	for key in sources/keys/*.asc; do sudo install -m 0644 "$$key" "$(APT_KEY_DIR)/$${key##*/}"; done
	for key in sources/keys/*.gpg; do sudo install -m 0644 "$$key" "$(VENDOR_KEY_DIR)/$${key##*/}"; done
	temp=$$(mktemp)
	trap 'rm -f "$$temp"' EXIT
	for file in sources/*.sources; do
	    sed "s/@UBUNTU_CODENAME@/$${UBUNTU_CODENAME:-$$VERSION_CODENAME}/g" "$$file" > "$$temp"
	    sudo install -m 0644 "$$temp" "$(APT_SOURCE_DIR)/$${file##*/}"
	done

.PHONY: repos
repos: sources-install
	@$(helpers)
	read_list apt-repos.txt
	repositories=("$${entries[@]}")
	if ! command -v extrepo >/dev/null 2>&1; then
	    sudo apt-get update
	    sudo apt-get install --yes extrepo
	fi
	for repository in "$${repositories[@]}"; do
	    printf 'Enabling APT repository: %s\n' "$$repository"
	    if ! sudo extrepo enable "$$repository"; then
	        printf 'Could not enable repository %s from apt-repos.txt.\n' "$$repository" >&2
	        exit 1
	    fi
	done
	sudo apt-get update

.PHONY: nix-install
nix-install: apt-install
	@$(helpers)
	if ! command -v nix >/dev/null 2>&1 && [[ ! -x /nix/var/nix/profiles/default/bin/nix ]] && ! systemctl is-active --quiet nix-daemon.service; then
	    sudo apt-get install --yes nix-bin nix-setup-systemd
	fi
	if getent group nix-users >/dev/null && ! id -nG "$$(id -un)" | tr ' ' '\n' | grep -Fxq nix-users; then
	    sudo usermod --append --groups nix-users "$$(id -un)"
	    printf 'Added you to nix-users. Reboot to refresh group membership in all sessions.\n'
	fi
	if systemctl is-active --quiet nix-daemon.service; then
	    printf 'Using the existing active Nix daemon.\n'
	else
	    sudo systemctl enable --now nix-daemon.socket
	fi
	stow_config nix "$(CONFIG_HOME)"

.PHONY: nvim-install
nvim-install: apt-install
	@$(helpers)
	stow_config nvim "$(CONFIG_HOME)"
	while read -r name url revision; do
	    checkout "$(CONFIG_HOME)/nvim/pack/plugins/start/$$name" "$$url" "$$revision"
	done < config/nvim/plugins.txt

.PHONY: kitty-install
kitty-install: apt-install
	@$(helpers)
	stow_config kitty "$(CONFIG_HOME)"

.PHONY: shell-install
shell-install: apt-install
	@$(helpers)
	checkout "$(DATA_HOME)/deps/oh-my-zsh" https://github.com/ohmyzsh/ohmyzsh.git 50550c70eaa36e79fdf380bdc4ddad4a1ad581a0
	stow_config shell "$(HOME)"
	chsh -s /usr/bin/zsh
	printf 'Start a new terminal to load Oh My Zsh, z and direnv.\n'

.PHONY: git-install
git-install: apt-install
	@$(helpers)
	stow_config git "$(CONFIG_HOME)"
	include_git_config
	printf 'Sign in to 1Password and enable its SSH agent; SSH configuration is left as already migrated.\n'

.PHONY: nfs-install
nfs-install: apt-install
	@if [[ ! -d /srv/data ]]; then sudo install -d -m 0755 /srv/data; fi
	temp=$$(mktemp)
	trap 'rm -f "$$temp"' EXIT
	awk '!($$1 !~ /^#/ && $$2 == "/srv/data")' "$(FSTAB)" > "$$temp"
	cat config/system/fstab.nfs >> "$$temp"
	sudo findmnt --verify --tab-file "$$temp"
	if ! cmp -s "$$temp" "$(FSTAB)"; then
	    sudo cp -a --backup=numbered "$(FSTAB)" "$(FSTAB).deps-backup"
	    sudo install -m 0644 "$$temp" "$(FSTAB)"
	fi
	sudo systemctl daemon-reload
	if ! mountpoint -q /srv/data; then sudo systemctl start srv-data.automount; fi
	printf 'NFS automount configured. Check server UID/GID permissions before changing ownership.\n'

.PHONY: books-install
books-install: apt-install
	@install -d "$(CACHE_HOME)/deps/debs"
	apt_temp=$$(mktemp -d /tmp/deps-debs.XXXXXXXX)
	trap 'rm -rf -- "$$apt_temp"' EXIT
	chmod 0755 "$$apt_temp"
	while read -r name url checksum; do
	    [[ -z $$name || $$name == \#* ]] && continue
	    file="$(CACHE_HOME)/deps/debs/$${url##*/}"
	    if [[ ! -f $$file ]] || ! printf '%s  %s\n' "$$checksum" "$$file" | sha256sum --check --status; then
	        curl --fail --location --silent --show-error "$$url" --output "$$file.part"
	        printf '%s  %s\n' "$$checksum" "$$file.part" | sha256sum --check --status
	        mv "$$file.part" "$$file"
	    fi
	    staged="$$apt_temp/$${file##*/}"
	    install -m 0644 -- "$$file" "$$staged"
	    sudo apt-get install --yes -- "$$staged"
	done < book-debs.txt

.PHONY: obsidian-check
obsidian-check:
	@vault="$(VAULT)"
	[[ -n $$vault ]] || { printf 'Usage: make obsidian-check VAULT=/path/to/vault\n' >&2; exit 1; }
	config="$$vault/.obsidian"
	jq -e 'type == "array" and all(.[]; type == "string")' "$(OBSIDIAN_PLUGINS)" >/dev/null
	mapfile -t plugins < <(jq -r '.[]' "$(OBSIDIAN_PLUGINS)")
	for plugin in "$${plugins[@]}"; do
	    jq -e --arg plugin "$$plugin" 'index($$plugin) != null' "$$config/community-plugins.json" >/dev/null && \
	        [[ -f "$$config/plugins/$$plugin/manifest.json" && -f "$$config/plugins/$$plugin/main.js" ]] || \
	        { printf 'Plugin missing or disabled: %s\n' "$$plugin" >&2; exit 1; }
	done
	printf 'All expected community plugins are installed and enabled.\n'

.PHONY: ai-preflight
ai-preflight:
	@$(helpers)
	load_node
	command -v node >/dev/null && command -v npm >/dev/null || { printf 'Node.js/npm not found. Run make toolchains, or activate your Node toolchain.\n' >&2; exit 1; }
	node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (major < 22 || (major === 22 && minor < 19)) { console.error("AI tools require Node.js 22.19 or newer."); process.exit(1); }'
	[[ -r ai-tools.txt ]] || { printf 'Cannot read ai-tools.txt\n' >&2; exit 1; }

.PHONY: ai-install
ai-install: ai-preflight
	@$(helpers)
	load_node
	read_list ai-tools.txt
	(($${#entries[@]})) || { printf 'No npm packages in ai-tools.txt\n' >&2; exit 1; }
	install -d "$(AI_NPM_PREFIX)/bin"
	prefix="$$(cd "$(AI_NPM_PREFIX)" && pwd -P)"
	backups=()
	for tool in codex pi claude; do
	    target="$$prefix/bin/$$tool"
	    if [[ -e $$target || -L $$target ]]; then
	        case "$$(readlink -m -- "$$target")" in
	            "$$prefix/lib/node_modules/@openai/codex/"*|"$$prefix/lib/node_modules/@earendil-works/pi-coding-agent/"*|"$$prefix/lib/node_modules/@anthropic-ai/claude-code/"*) continue ;;
	        esac
	        [[ ! -d $$target || -L $$target ]] || { printf 'Expected an executable file: %s\n' "$$target" >&2; exit 1; }
	        mv -T --backup=numbered -- "$$target" "$$target.deps-backup"
	        backups+=("$$target")
	    fi
	done
	if ! npm install --global --prefix "$$prefix" --include=optional -- "$${entries[@]}"; then
	    for target in "$${backups[@]}"; do
	        rm -f -- "$$target"
	        mv -T -- "$$target.deps-backup" "$$target"
	    done
	    exit 1
	fi
	for tool in codex pi claude; do "$$prefix/bin/$$tool" --version; done
	printf 'Installed AI packages in %s. Ensure %s/bin is on PATH.\n' "$$prefix" "$$prefix"

.PHONY: ai-check
ai-check:
	@$(helpers)
	load_node
	for tool in codex pi claude; do
	    command -v "$$tool" || { printf '%s is not on PATH; run make ai-install and open a fresh terminal.\n' "$$tool" >&2; exit 1; }
	    "$$tool" --version
	done

.PHONY: tailscale-install
tailscale-install: apt-install
	@sudo systemctl enable --now tailscaled
	tailscale version
	printf 'To join your tailnet, run: sudo tailscale up\n'

.PHONY: meetily-build
meetily-build:
	@$(helpers)
	shopt -s nullglob
	packages=("$(MEETILY_DIR)"/target/release/bundle/deb/*.deb)
	if [[ "$(MEETILY_FORCE)" != 1 && $${#packages[@]} -eq 1 ]]; then
	    printf 'Reusing Meetily package: %s\n' "$${packages[0]}"
	    exit 0
	fi
	$(MAKE) apt-install
	load_node
	command -v node >/dev/null && command -v npm >/dev/null && command -v cargo >/dev/null && command -v rustc >/dev/null || { printf 'Node.js/npm and Rust are required; run make toolchains first.\n' >&2; exit 1; }
	case "$(MEETILY_GPU)" in vulkan|cuda|cpu) ;; *) printf 'MEETILY_GPU must be vulkan, cuda or cpu.\n' >&2; exit 1 ;; esac
	checkout "$(MEETILY_DIR)" "$(MEETILY_URL)" "$(MEETILY_REVISION)"
	install -d "$(MEETILY_TOOLS)"
	npm install --prefix "$(MEETILY_TOOLS)" --no-save --package-lock=false pnpm@$(MEETILY_PNPM_VERSION)
	export PATH="$(MEETILY_TOOLS)/node_modules/.bin:$$PATH"
	cd "$(MEETILY_DIR)/frontend"
	pnpm install --frozen-lockfile
	features=()
	if [[ "$(MEETILY_GPU)" != cpu ]]; then features=(--features "$(MEETILY_GPU)"); fi
	cargo build --locked --release --manifest-path ../llama-helper/Cargo.toml "$${features[@]}"
	triple=$$(rustc -vV | awk '/^host:/ { print $$2 }')
	install -d src-tauri/binaries
	install -m 0755 "../target/release/llama-helper" "src-tauri/binaries/llama-helper-$$triple"
	pnpm exec tauri build --bundles deb --config '{"bundle":{"createUpdaterArtifacts":false}}' -- --locked "$${features[@]}"

.PHONY: meetily-install
meetily-install:
	@if [[ "$(MEETILY_FORCE)" != 1 && "$$(dpkg-query -W -f='$${Status}' meetily 2>/dev/null || true)" == 'install ok installed' ]]; then
	    printf 'Meetily is already installed.\n'
	    exit 0
	fi
	$(MAKE) meetily-build
	shopt -s nullglob
	packages=("$(MEETILY_DIR)"/target/release/bundle/deb/*.deb)
	[[ $${#packages[@]} == 1 ]] || { printf 'Expected one Meetily Debian package. Inspect %s/target/release/bundle/deb\n' "$(MEETILY_DIR)" >&2; exit 1; }
	apt_temp=$$(mktemp -d /tmp/deps-meetily.XXXXXXXX)
	trap 'rm -rf -- "$$apt_temp"' EXIT
	chmod 0755 "$$apt_temp"
	install -m 0644 "$${packages[0]}" "$$apt_temp/meetily.deb"
	sudo apt-get install --yes -- "$$apt_temp/meetily.deb"

.PHONY: steam-install
steam-install:
	@packages=()
	while IFS=$$'\t' read -r package architecture status version; do
	    if [[ $$architecture == amd64 && $$status == ii* && $$package =~ ^libnvidia-gl(-([0-9]+)(-server)?)?$$ ]]; then
	        branch=$${BASH_REMATCH[2]:-}
	        if [[ -z $$branch || $${version#*:} == "$$branch".* ]]; then packages+=("$$package:i386"); fi
	    fi
	done < <(dpkg-query -W -f='$${Package}\t$${Architecture}\t$${db:Status-Abbrev}\t$${Version}\n' 'libnvidia-gl*' 2>/dev/null || true)
	[[ $${#packages[@]} == 1 ]] || { printf 'Expected one installed NVIDIA graphics library. Inspect: nvidia-smi; dpkg -l "libnvidia-gl*"\n' >&2; exit 1; }
	sudo dpkg --add-architecture i386
	sudo apt-get update
	sudo apt-get install --yes --install-recommends steam-installer "$${packages[@]}"

.PHONY: libraries-plan libraries-copy
libraries-plan libraries-copy:
	@library_source="$(LIBRARY_SOURCE)"
	[[ -n $$library_source ]] || { printf 'Set LIBRARY_SOURCE=user@old-laptop:/home/oscar\n' >&2; exit 1; }
	target="$@"
	flags=()
	if [[ $$target == libraries-plan ]]; then flags+=(--dry-run); fi
	rsynchronise_backup="$(DATA_HOME)/deps/library-backups/$$(date +%Y%m%d-%H%M%S)"
	rsync -ar --no-owner --no-group --ignore-missing-args --backup --backup-dir="$$rsynchronise_backup" "$${flags[@]}" --files-from=config/library-paths.txt "$$library_source/" "$(HOME)/"

.PHONY: autoremove
autoremove:
	sudo apt autoremove --yes

.PHONY: update
update:
	sudo apt-get update --yes
	sudo apt list > aptfile.manifest

.PHONY: upgrade
upgrade:
	sudo apt-get upgrade --yes
	sudo apt list > aptfile.manifest

.PHONY: lts-upgrade
lts-upgrade: update
	sudo apt full-upgrade --yes
	sudo do-release-upgrade

.PHONY: flatpak-install
flatpak-install: apt-install
	@$(helpers)
	read_list flatpakfile.txt
	sudo flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
	if (($${#entries[@]})); then
	    sudo flatpak install --system --noninteractive -y flathub "$${entries[@]}"
	fi
	flatpak list > flatpak.manifest

.PHONY: flatpak-update
flatpak-update:
	sudo flatpak update --system -y --noninteractive
	flatpak list > flatpak.manifest

.PHONY: manifest
manifest:
	sudo apt list > aptfile.manifest
	flatpak list > flatpak.manifest

.PHONY: toolchains
toolchains:
	@command -v curl >/dev/null
	@command -v git >/dev/null
	curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh | sh
	curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
	@set -eu; \
	export NVM_DIR="$${NVM_DIR:-$$HOME/.nvm}"; \
	if [ ! -s "$$NVM_DIR/nvm.sh" ]; then \
		git clone https://github.com/nvm-sh/nvm.git "$$NVM_DIR"; \
		tag=$$(git -C "$$NVM_DIR" tag --list 'v[0-9]*' --sort=-version:refname | head -n 1); \
		git -C "$$NVM_DIR" checkout "$$tag"; \
	fi; \
	. "$$NVM_DIR/nvm.sh"; \
	nvm install --lts=krypton; \
	nvm alias default lts/krypton; \
	line='export NVM_DIR="$$HOME/.nvm"; [ ! -s "$$NVM_DIR/nvm.sh" ] || . "$$NVM_DIR/nvm.sh"'; \
	for profile in "$$HOME/.bashrc" "$${ZDOTDIR:-$$HOME}/.zshrc"; do \
		touch "$$profile"; \
		grep -Fqx "$$line" "$$profile" || printf '\n%s\n' "$$line" >> "$$profile"; \
	done
