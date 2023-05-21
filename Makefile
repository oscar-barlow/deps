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

.PHONY: snap-install
install: refresh
	cat snapfile.txt | xargs sudo snap install

.PHONY: snap-refresh
refresh:
	sudo snap refresh
