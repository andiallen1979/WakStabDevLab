# Copyright 2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2
EAPI=8
DESCRIPTION="DevLab (~amd64) Portage configuration files"
HOMEPAGE="https://github.com/andiallen1979/WakStabDevLab.git"
S="${WORKDIR}"
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="amd64 ~amd64"
src_install() {
	insinto /etc/portage
	doins -r "${FILESDIR}"/*
}
