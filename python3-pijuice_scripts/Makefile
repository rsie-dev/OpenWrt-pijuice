include $(TOPDIR)/rules.mk

PKG_NAME:=python3-pijuice_scripts
PKG_VERSION:=1.0
PKG_RELEASE:=1

# Source settings (i.e. where to find the source codes)
# This is a custom variable, used below
SOURCE_DIR:=/var/tmp/openwrt/OpenWrt-pijuice/python3-pijuice_scripts
#PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz

include $(INCLUDE_DIR)/package.mk
include $(TOPDIR)/feeds/packages/lang/python/python3-package.mk

PYTHON3_PKG_SETUP_VARS:=PIJUICE_VERSION=$(PKG_VERSION)

define Package/python3-pijuice_scripts
  SECTION:=system
  CATEGORY:=System
  TITLE:=PiJuice Scripts
  DEPENDS:= \
  	+python3-light \
  	+python3-logging \
	+python3-pijuice
endef

define Package/python3-pijuice_scripts/description
	Scripts to work with pijuice
	https://github.com/PiSupply/PiJuice
endef

# The last command is necessary to ensure our preparation instructions remain compatible with the patching system.
define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	cp $(SOURCE_DIR)/files/* $(PKG_BUILD_DIR)
	$(Build/Patch)
endef

$(eval $(call Py3Package,python3-pijuice_scripts))
$(eval $(call BuildPackage,python3-pijuice_scripts))
$(eval $(call BuildPackage,python3-pijuice_scripts-src))
