SHELL = /bin/bash

.PHONY: install
install: repos update
	cat aptfile.txt | grep -v '#' | xargs apt install --yes
	apt autoremove --yes

.PHONY: repos
repos:
	mkdir -p /usr/share/keyrings
	test -f /usr/share/keyrings/docker-archive-keyring.gpg || curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
	test -f /usr/share/keyrings/tailscale-archive-keyring.gpg || curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
	cat repositories.txt | sed "s/\$$(lsb_release -cs)/$$(grep VERSION_CODENAME /etc/os-release | cut -d= -f2)/g" > /tmp/repos.tmp
	while read line; do grep -Fxq "$$line" /etc/apt/sources.list.d/custom-repos.list 2>/dev/null || echo "$$line" >> /etc/apt/sources.list.d/custom-repos.list; done < /tmp/repos.tmp
	rm -f /tmp/repos.tmp

.PHONY: update
update:
	apt-get update --yes

.PHONY: upgrade
upgrade:
	apt-get upgrade --yes
