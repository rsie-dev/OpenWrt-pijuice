include $(TOPDIR)/rules.mk

PKG_NAME:=python3-pijuice
PKG_VERSION:=1.8
PKG_RELEASE:=1

# Source settings (i.e. where to find the source codes)
# This is a custom variable, used below
SOURCE_DIR:=/home/sieger/pijuice/OpenWrt-pijuice/python3-pijuice
#PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz

PKG_SOURCE_PROTO:=git
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.bz2
PKG_SOURCE_URL:=https://github.com/PiSupply/PiJuice.git
PKG_SOURCE_VERSION:=1e1049de39800862079a309d94133fe5d8e9a856
PKG_MIRROR_HASH:=7e4bff14cd58f2b9af8772888966b83a139c778a7ed1a7104b28a419170ebff1


include $(INCLUDE_DIR)/package.mk
include $(TOPDIR)/feeds/packages/lang/python/python3-package.mk

PYTHON3_PKG_SETUP_VARS:=PIJUICE_VERSION=$(PKG_VERSION)

define Package/python3-pijuice
  SECTION:=system
  CATEGORY:=System
  TITLE:=PiJuice
  DEPENDS:= \
  	+python3-light \
  	+python3-logging \
	+python3-smbus \
	+python3-ctypes
  EXTRA_DEPENDS:= \
	sudo
#	kmod-i2c-smbus \
#	kmod-i2c-bcm2835
endef

define Package/python3-pijuice/description
	OpenWrt package of PiJuice software:
	https://github.com/PiSupply/PiJuice

	Additionally these OpenWrt packages need to be installed, too:
	- kmod-i2c-smbus
	- kmod-i2c-bcm2835

	Enable i2c on the pi:
	Set in config.txt:
	dtparam=i2c_arm=on
	dtparam=spi=on
	dtparam=i2s=on
endef

# The last command is necessary to ensure our preparation instructions remain compatible with the patching system.
define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(HOST_TAR) -C $(PKG_BUILD_DIR) --strip-components=3 -xjf $(DL_DIR)/$(PKG_SOURCE) $(PKG_NAME)-$(PKG_VERSION)/Software/Source
	$(HOST_TAR) -C $(PKG_BUILD_DIR) --strip-components=2 -xjf $(DL_DIR)/$(PKG_SOURCE) $(PKG_NAME)-$(PKG_VERSION)/Software/Test
	cp -r $(SOURCE_DIR)/files/* $(PKG_BUILD_DIR)
	$(Build/Patch)
endef

define Package/$(PKG_NAME)/install
	$(call Py3Package/$(PKG_NAME)/install,$(1))
	$(call Py3Package/ProcessFilespec,$(PKG_NAME),$(PKG_INSTALL_DIR),$(1))
	$(FIND) $(1) -name '*.exe' -delete
	$(call Python3/CompileAll,$(1))
	$(call Python3/DeleteSourceFiles,$(1))
	$(call Python3/DeleteEmptyDirs,$(1))
	if [ -d "$(1)/usr/bin" ]; then \
		$(call Python3/FixShebang,$(1)/usr/bin/*) ; \
	fi
	
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/pijuice_util $(1)/usr/bin

	$(INSTALL_DIR) $(1)/etc/pijuice
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/pijuice_config.JSON $(1)/etc/pijuice

	$(INSTALL_DIR) $(1)/usr/share/pijuice/data/firmware
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/data/firmware/* $(1)/usr/share/pijuice/data/firmware

	$(INSTALL_DIR) $(1)/etc/init.d/
	$(INSTALL_BIN) ./files/pijuice.init $(1)/etc/init.d/pijuice
endef

define Package/$(PKG_NAME)-src/install
	$(call Py3Package/$(PKG_NAME)/install,$(1))
	$(call Py3Package/ProcessFilespec,$(PKG_NAME),$(PKG_INSTALL_DIR),$(1))
	$(call Python3/DeleteNonSourceFiles,$(1))
	$(call Python3/DeleteEmptyDirs,$(1))
endef

$(eval $(call Py3Package,python3-pijuice))
$(eval $(call BuildPackage,python3-pijuice))
$(eval $(call BuildPackage,python3-pijuice-src))
