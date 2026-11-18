EAPI=8
DESCRIPTION="Unbranded Gentoo profile builder, registry client, and offline compressed handbooks"
HOMEPAGE="https://fragtoo.com"
S="${WORKDIR}"
LICENSE="MIT"
SLOT="0"
KEYWORDS="amd64 ~amd64 arm64 ~arm64"
RDEPEND="dev-lang/python:*"
src_install() {
	dobin "${FILESDIR}/gentool-profiles"
	insinto /usr/share/gentool-profiles
	doins "${FILESDIR}"/handbook-*.txt.gz
}
