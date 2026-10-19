SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:

.PHONY: install
install:
	@read_list() {
	    local entry
	    entries=()
	    while IFS= read -r entry || [[ -n $$entry ]]; do
	        entry="$${entry#"$${entry%%[![:space:]]*}"}"
	        entry="$${entry%"$${entry##*[![:space:]]}"}"
	        [[ -z $$entry || $$entry == \#* ]] && continue
	        entries+=("$$entry")
	    done < "$$1"
	}
	read_list apt-repos.txt
	repositories=("$${entries[@]}")
	read_list aptfile.txt
	packages=("$${entries[@]}")
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
	if (($${#packages[@]})); then
	    sudo apt-get install --yes -- "$${packages[@]}"
	fi
	apt list > aptfile.manifest

.PHONY: autoremove
autoremove:
	sudo apt autoremove --yes

.PHONY: check
check:
	python3 -B -m unittest discover -s tests -v

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
flatpak-install: 
	cat flatpakfile.txt | xargs flatpak install -y --noninteractive 
	flatpak list > flatpak.manifest

.PHONY: flatpak-update
flatpak-update:
	cat flatpakfile.txt | xargs flatpak update -y --noninteractive
	flatpak list > flatpak.manifest

.PHONY: manifest
manifest:
	sudo apt list > aptfile.manifest
	flatpak list > flatpak.manifest
