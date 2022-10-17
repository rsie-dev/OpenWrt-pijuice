include $(TOPDIR)/rules.mk

PKG_NAME:=python3-pijuice_scripts
PKG_VERSION:=1.0
PKG_RELEASE:=1

# Source settings (i.e. where to find the source codes)
# This is a custom variable, used below
SOURCE_DIR:=/home/sieger/pijuice/OpenWrt-pijuice/python3-pijuice_scripts
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
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/pijuice_ctl $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/pijuice_status  $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/pijuice_poweroff $(1)/usr/bin
endef

define Package/$(PKG_NAME)-src/install
	$(call Py3Package/$(PKG_NAME)/install,$(1))
	$(call Py3Package/ProcessFilespec,$(PKG_NAME),$(PKG_INSTALL_DIR),$(1))
	$(call Python3/DeleteNonSourceFiles,$(1))
	$(call Python3/DeleteEmptyDirs,$(1))
endef

$(eval $(call Py3Package,python3-pijuice_scripts))
$(eval $(call BuildPackage,python3-pijuice_scripts))
$(eval $(call BuildPackage,python3-pijuice_scripts-src))
