# Copyright 2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2
EAPI=8
DESCRIPTION="Declarative bootloader and Secure Boot switcher for Gentool hosts"
HOMEPAGE="https://codeberg.org"
S="${WORKDIR}"
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="amd64 arm64"
IUSE="+grub systemd-boot refind secureboot"
REQUIRED_USE="^^ ( grub systemd-boot refind ) secureboot? ( systemd-boot )"
RDEPEND="
	sys-boot/efibootmgr
	sys-kernel/dracut
	sys-kernel/installkernel
	grub? ( sys-boot/grub )
	systemd-boot? ( sys-apps/systemd )
	refind? ( sys-boot/refind )
	secureboot? ( app-crypt/sbctl )
"
src_install() {
	dobin "${FILESDIR}"/gentool-switch-*
	insinto /etc/kernel
	use systemd-boot && newins "${FILESDIR}/install-bls.conf" install.conf || newins "${FILESDIR}/install-grub.conf" install.conf
	insinto /etc/kernel/config.d
	use secureboot && newins "${FILESDIR}/module-sign-on.config" module-sign.config || newins "${FILESDIR}/module-sign-off.config" module-sign.config
}
pkg_postinst() {
	[[ "${ROOT:-/}" == "/" ]] || return 0
	if use grub; then /usr/bin/gentool-switch-grub --no-emerge
	elif use systemd-boot; then /usr/bin/gentool-switch-systemdboot $(usex secureboot "--secureboot" "") --no-emerge
	elif use refind; then /usr/bin/gentool-switch-refind --no-emerge; fi
}
