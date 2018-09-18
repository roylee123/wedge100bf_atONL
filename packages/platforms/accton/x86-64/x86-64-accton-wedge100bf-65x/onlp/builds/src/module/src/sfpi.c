/************************************************************
 * <bsn.cl fy=2014 v=onl>
 *
 *           Copyright 2014 Big Switch Networks, Inc.
 *           Copyright 2016 Accton Technology Corporation.
 *
 * Licensed under the Eclipse Public License, Version 1.0 (the
 * "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at
 *
 *        http://www.eclipse.org/legal/epl-v10.html
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific
 * language governing permissions and limitations under the
 * License.
 *
 * </bsn.cl>
 ************************************************************
 *
 *
 *
 ***********************************************************/
#include <onlplib/i2c.h>
#include <onlp/platformi/sfpi.h>
#include <onlplib/file.h>
#include "platform_lib.h"

#include "x86_64_accton_wedge100bf_65x_log.h"

#define BIT(i)          (1 << (i))
#define NUM_OF_SFP_PORT 64
#define ABSENT_CHAR     '1'
/************************************************************
 *
 * SFPI Entry Points
 *
 ***********************************************************/
int
onlp_sfpi_init(void)
{
    /* Called at initialization time */    
    return ONLP_STATUS_OK;
}

int
onlp_sfpi_bitmap_get(onlp_sfp_bitmap_t* bmap)
{
    /*
     * Ports {0, 32}
     */
    int p;
    AIM_BITMAP_CLR_ALL(bmap);

    for(p = 0; p < NUM_OF_SFP_PORT; p++) {
        AIM_BITMAP_SET(bmap, p);
    }

    return ONLP_STATUS_OK;
}

int
onlp_sfpi_is_present(int port)
{
    /*
     * Return 1 if present.
     * Return 0 if not present.
     * Return < 0 if error.
     */
    int ret;
    char prs[2], cmd[64];
    char prefix[] = "onlp_sfp_poll.py presence -p %d";

    sprintf(cmd, prefix, port);
    ret = _run_shell_cmd(cmd, prs, sizeof(prs));
    if (ret != 0) {
        return ONLP_STATUS_E_INTERNAL;
    }

    return !(prs[0] == ABSENT_CHAR);
}

int
onlp_sfpi_presence_bitmap_get(onlp_sfp_bitmap_t* dst)
{
    int i, value;
    int ret;
    char prs[NUM_OF_SFP_PORT+1];
    char cmd[] = "onlp_sfp_poll.py presence";

    ret = _run_shell_cmd(cmd, prs, sizeof(prs));
    if (ret != 0) {
            return ONLP_STATUS_E_INTERNAL;
        }

    /* Populate bitmap */
    for(i = 0; i<NUM_OF_SFP_PORT; i++) {
        value = !(ABSENT_CHAR == prs[i]);
        AIM_BITMAP_MOD(dst, i, value);
    }
    return ONLP_STATUS_OK;
}

int
onlp_sfpi_rx_los_bitmap_get(onlp_sfp_bitmap_t* dst)
{
    return ONLP_STATUS_OK;
}

static int
sfpi_eeprom_read(int port, uint8_t devaddr, uint8_t data[256])
{
    memset(data, 0, 256);
    if (devaddr == 0x51)
    {
        return ONLP_STATUS_OK;
    }
    {
        int ret;
        char cmd[64];
        char prefix[] = "onlp_sfp_poll.py eeprom -p %d";

        sprintf(cmd, prefix, port);
        ret = _run_shell_cmd(cmd, (char*)data, 256);
        if (ret != 0) {
            return ONLP_STATUS_E_INTERNAL;
        }
    }

    return ONLP_STATUS_OK;
}


int
onlp_sfpi_eeprom_read(int port, uint8_t data[256])
{
    return sfpi_eeprom_read(port, 0x50, data);
}

int
onlp_sfpi_dom_read(int port, uint8_t data[256])
{
    return sfpi_eeprom_read(port, 0x51, data);
}

int
onlp_sfpi_control_set(int port, onlp_sfp_control_t control, int value)
{
    return ONLP_STATUS_E_UNSUPPORTED;
}

int
onlp_sfpi_control_get(int port, onlp_sfp_control_t control, int* value)
{
    return ONLP_STATUS_E_UNSUPPORTED;
}

int
onlp_sfpi_denit(void)
{
    return ONLP_STATUS_OK;
}

