SHELL = /bin/bash

.PHONY: install
install: repos update
	cat aptfile.txt | grep -v '#' | xargs sudo apt install --yes
	sudo apt autoremove --yes

.PHONY: repos
repos:
	@echo "Installing GPG keys..."
	@sudo mkdir -p /usr/share/keyrings
	@curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg || echo "Failed to install Docker GPG key"
	@curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null || echo "Failed to install Tailscale GPG key"
	@echo "Adding repositories..."
	@while IFS= read -r line; do \
		case "$$line" in \
			deb*) \
				expanded_line=$$(echo "$$line" | sed "s/\$$(lsb_release -cs)/$$(grep VERSION_CODENAME /etc/os-release | cut -d= -f2)/g"); \
				echo "Checking repository: $$expanded_line"; \
				if ! grep -Fxq "$$expanded_line" /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null; then \
					echo "Adding repository: $$expanded_line"; \
					echo "$$expanded_line" | sudo tee -a /etc/apt/sources.list.d/custom-repos.list; \
				else \
					echo "Repository already exists: $$expanded_line"; \
				fi; \
				;; \
		esac; \
	done < <(cat repositories.txt)

.PHONY: update
update:
	sudo apt-get update --yes

.PHONY: upgrade
upgrade:
	sudo apt-get upgrade --yes
