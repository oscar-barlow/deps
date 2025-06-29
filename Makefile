SHELL = /bin/bash

.PHONY: install
install: repos update
	cat aptfile.txt | grep -v '#' | xargs sudo apt install --yes
	sudo apt autoremove --yes

.PHONY: repos
repos:
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
