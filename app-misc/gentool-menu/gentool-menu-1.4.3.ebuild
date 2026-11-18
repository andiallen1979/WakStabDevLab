# Copyright 2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2
EAPI=8
DISTUTILS_USE_PEP517=setuptools
PYTHON_COMPAT=( python3_{11..15} )
inherit distutils-r1
DESCRIPTION="Kconfig menuconfig TUI for toggling Portage USE flags across installed packages"
HOMEPAGE="https://codeberg.org"
S="${WORKDIR}/${P}"
LICENSE="MIT"
SLOT="0"
KEYWORDS="amd64 ~amd64 arm64 ~arm64"
RDEPEND="dev-python/kconfiglib[${PYTHON_USEDEP}] sys-apps/portage[${PYTHON_USEDEP}]"
src_unpack() { mkdir -p "${S}"; cp -r "${FILESDIR}"/* "${S}/" || die; }
