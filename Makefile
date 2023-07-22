.PHONY: install
install: update
	cat aptfile.txt | grep -v '#' | xargs sudo apt install --yes
	sudo apt autoremove --yes

.PHONY: update
update:
	sudo apt-get update --yes

.PHONY: upgrade
upgrade:
	sudo apt-get upgrade --yes

PHONY: snap-install
snap-install: snap-refresh
	cat snapfile.txt | xargs sudo snap install
	sudo snap list > snapfile.manifest

.PHONY: snap-refresh
snap-refresh:
	sudo snap refresh
	sudo snap list > snapfile.manifest
