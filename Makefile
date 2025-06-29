.PHONY: install
install: repos update
	cat aptfile.txt | grep -v '#' | xargs sudo apt install --yes
	sudo apt autoremove --yes

.PHONY: repos
repos:
	@while IFS= read -r line; do \
		if [[ "$$line" =~ ^deb.*$$ ]]; then \
			echo "Checking repository: $$line"; \
			if ! grep -Fxq "$$line" /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null; then \
				echo "Adding repository: $$line"; \
				echo "$$line" | sudo tee -a /etc/apt/sources.list.d/custom-repos.list; \
			else \
				echo "Repository already exists: $$line"; \
			fi; \
		fi; \
	done < repositories.txt

.PHONY: update
update:
	sudo apt-get update --yes

.PHONY: upgrade
upgrade:
	sudo apt-get upgrade --yes
