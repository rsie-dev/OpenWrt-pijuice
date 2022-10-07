include $(TOPDIR)/rules.mk

PKG_NAME:=python3-pijuice
PKG_VERSION:=1.8
PKG_RELEASE:=1

# Source settings (i.e. where to find the source codes)
# This is a custom variable, used below
SOURCE_DIR:=/var/tmp/openwrt/OpenWrt-pijuice/python3-pijuice
#PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz

PKG_SOURCE_PROTO:=git
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.bz2
PKG_SOURCE_URL:=https://github.com/PiSupply/PiJuice.git
PKG_SOURCE_VERSION:=1e1049de39800862079a309d94133fe5d8e9a856
# PKG_MIRROR_HASH:=86e1978a31d57251b293cdeea3cc16e5dea13c01ece87d6cc916d7317411166e
PKG_MIRROR_HASH:=7e4bff14cd58f2b9af8772888966b83a139c778a7ed1a7104b28a419170ebff1

PKG_UNPACK=$(HOST_TAR) -C $(PKG_BUILD_DIR) --strip-components=3 -xjf $(DL_DIR)/$(PKG_SOURCE) $(PKG_NAME)-$(PKG_VERSION)/Software/Source

include $(INCLUDE_DIR)/package.mk
include $(TOPDIR)/feeds/packages/lang/python/python3-package.mk

PYTHON3_PKG_SETUP_VARS:=PIJUICE_VERSION=$(PKG_VERSION)

# Package definition; instructs on how and where our package will appear in the overall configuration menu ('make menuconfig')
define Package/python3-pijuice
  SECTION:=system
  CATEGORY:=System
  TITLE:=PiJuice
  DEPENDS:= \
  	+python3-base \
	+python3-smbus \
	+python3-ctypes
#  EXTRA_DEPENDS:= \
#	kmod-i2c-smbus \
#	kmod-i2c-bcm2835
endef

# Package description; a more verbose description on what our package does
define Package/python3-pijuice/description
	OpenWrt package of PiJuice software:
	https://github.com/PiSupply/PiJuice
endef

# Package preparation instructions; create the build directory and copy the source code. 
# The last command is necessary to ensure our preparation instructions remain compatible with the patching system.
define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(PKG_UNPACK)
	cp $(SOURCE_DIR)/files/* $(PKG_BUILD_DIR)
	$(Build/Patch)
endef

#define Package/python3-pijuice/install
#endef

# This command is always the last, it uses the definitions and variables we give above in order to get the job done
$(eval $(call Py3Package,python3-pijuice))
$(eval $(call BuildPackage,python3-pijuice))
$(eval $(call BuildPackage,python3-pijuice-src))
