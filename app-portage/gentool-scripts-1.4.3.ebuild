# Copyright 2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2
EAPI=8
DESCRIPTION="Host-agnostic Portage and overlay helper scripts for Gentool systems"
HOMEPAGE="https://codeberg.org"
S="${WORKDIR}"
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="amd64 arm64"
RDEPEND="app-shells/bash sys-apps/portage"
src_unpack() { unpack "${FILESDIR}/gentool-scripts-bundle.tar.xz"; }
src_install() {
	dobin "${WORKDIR}"/{setpkgkw,setpkgenv,setpkguse,setpkgmask,cleanpkg,mknbdimg,gentool-repo-prep,gentool-sync-configs,gentool-push,gentool-bump,gentool-emptytree,gentool-audit}
}
