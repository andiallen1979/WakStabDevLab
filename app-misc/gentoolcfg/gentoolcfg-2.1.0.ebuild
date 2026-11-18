# Copyright 2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8
DISTUTILS_USE_PEP517=setuptools
PYTHON_COMPAT=( python3_{13..14} )
inherit desktop distutils-r1

DESCRIPTION="Portage configurator with Textual TUI, Qt6 GUI, Build Monitor, and Kernel Config manager"
HOMEPAGE="https://codeberg.org/andiallen1979/WakStab"
S="${WORKDIR}/${P}"
LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64 ~arm64"
IUSE="+gui qt6"

RDEPEND="
	app-portage/genlop
	x11-apps/xwininfo
	dev-python/textual[${PYTHON_USEDEP}]
	sys-apps/portage[${PYTHON_USEDEP}]
	gui? (
		qt6? ( dev-python/pyqt6[gui,widgets,${PYTHON_USEDEP}] )
	)
"

src_unpack() {
	mkdir -p "${S}" && tar -xJf "${FILESDIR}/gentoolcfg-core-${PV}.tar.xz" -C "${S}" || die
	tar -xJf "${FILESDIR}/gentoolcfg-gui-${PV}.tar.xz" -C "${S}" || die
	if ! use gui || ! use qt6; then rm -rf "${S}/gentoolcfg_qt6" "${S}/gentoolcfg-qt6.desktop" || die; fi
}

python_install_all() {
	distutils-r1_python_install_all
	use gui && use qt6 && domenu "${S}/gentoolcfg-qt6.desktop"
	insinto /usr/share/polkit-1/actions
	use gui && use qt6 && doins "${S}/org.wakstab.gentoolcfg.policy"
}
