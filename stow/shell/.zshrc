export ZSH="${XDG_DATA_HOME:-$HOME/.local/share}/deps/oh-my-zsh"
export PATH="$HOME/.local/bin:$PATH"

if [[ -r /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]]; then
    source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
fi

ZSH_THEME="mh"
plugins=(git z)
source "$ZSH/oh-my-zsh.sh"
source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

if [[ ${XDG_SESSION_TYPE:-} == wayland ]]; then
    alias clip='wl-copy'
else
    alias clip='xclip -selection clipboard'
fi

eval "$(direnv hook zsh)"

export NVM_DIR="$HOME/.nvm"; [ ! -s "$NVM_DIR/nvm.sh" ] || . "$NVM_DIR/nvm.sh"
