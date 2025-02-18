.PHONY: install
install: update
	cat aptfile.txt | grep -v '#' | xargs sudo apt install --yes
	sudo apt autoremove --yes
	sudo apt list > aptfile.manifest

.PHONY: update
update:
	sudo apt-get update --yes
	sudo apt list > aptfile.manifest

.PHONY: upgrade
upgrade:
	sudo apt-get upgrade --yes
	sudo apt list > aptfile.manifest

.PHONY: flatpak-install
flatpak-install: 
	cat flatpakfile.txt | xargs flatpak install -y 
	flatpak list > flatpak.manifest

.PHONY: flatpak-update
flatpak-update:
	cat flatpakfile.txt | xargs flatpak update -y 
	flatpak list > flatpak.manifest

.PHONY: manifest
manifest:
	sudo apt list > aptfile.manifest
	flatpak list > flatpak.manifest
