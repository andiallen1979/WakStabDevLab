# gentoolcfg

Unified Portage per-package configurator for Gentoo Linux featuring a Midnight Commander–inspired `ncurses` TUI (`gentoolcfg`) and optional native Qt6 (`gentoolcfg-qt6`), GTK3 (`gentoolcfg-gtk3`), and GTK4 (`gentoolcfg-gtk4`) frontends.

## Features
- **Desktop-Agnostic Frontends (`IUSE="+gui gtk3 gtk4 qt6"`):**
  - `gentoolcfg`: Always-built `ncurses` TUI with Midnight Commander skins (`modarin` default, `default`, `dark`, `gotar`, `nicedark`), mouse support, scrollbars, and `F1`–`F10` keybar.
  - `gentoolcfg-qt6`: Native PyQt6 GUI (`USE="gui qt6"`).
  - `gentoolcfg-gtk3` / `gentoolcfg-gtk4`: Native PyGObject GTK3/GTK4 GUIs (`USE="gui gtk3"` / `USE="gui gtk4"`).
  - `USE="-gui"`: Master override for a pure TUI-only install with zero GUI dependencies.
- **Per-Package Configuration Tabs:** Manage `package.use`, `package.env` (plus inline `.conf` profile editor), `package.accept_keywords` (`amd64`, `~amd64`, `**` with All/Exact/Forward scopes), `package.mask`, `package.unmask`, and `/etc/portage/patches/`.
- **Built-In System & Binhost Safeguards:**
  - Marks profile-locked (`use.force` / `use.mask`) flags with `*` and requires confirmation before overriding.
  - Runs a **Pre-Save Sanity Check & Change Report** before writing to `/etc/portage`, escalating warnings for core toolchain masks or `**` live keywords.
  - Automatically falls back to `./portage-preview/` when launched as a non-root user.
  - Integrates `genlop -t` build times to sort by slowest-compiling packages.
