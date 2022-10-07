
install and use SDK:
https://openwrt.org/docs/guide-developer/toolchain/using_the_sdk


build preparation:
- export path:
  export PATH=/home/buildbot/source/staging_dir/host/bin:$PATH

make menuconfig:
    - Automatic rebuild of packages
    - Automatic removal of build directories
    + Enable log files during build process
