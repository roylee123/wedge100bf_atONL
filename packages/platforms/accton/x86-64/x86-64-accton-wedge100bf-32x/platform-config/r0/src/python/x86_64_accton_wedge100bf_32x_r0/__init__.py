from onl.platform.base import *
from onl.platform.accton import *

class OnlPlatform_x86_64_accton_wedge100bf_32x_r0(OnlPlatformAccton,
                                                OnlPlatformPortConfig_32x100):
    MODEL="Wedge-100bf-32X"
    PLATFORM="x86-64-accton-wedge100bf-32x-r0"
    SYS_OBJECT_ID=".100.32.2"

    def baseconfig(self):
        #subprocess.call('depmod', shell=True)
        self.insmod('modprobe accton_wedge100bf_psensor model_id=1')

        return True
