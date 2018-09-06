from onl.platform.base import *
from onl.platform.accton import *

class OnlPlatform_x86_64_accton_wedge100bf_65x_r0(OnlPlatformAccton,
                                                OnlPlatformPortConfig_64x100):
    MODEL="Wedge-100bf-65x"
    PLATFORM="x86-64-accton-wedge100bf-65x-r0"
    SYS_OBJECT_ID=".100.65.1"

    def baseconfig(self):
        #subprocess.call('depmod', shell=True)
        self.insmod('modprobe accton_wedge100bf_psensor')

        return True
