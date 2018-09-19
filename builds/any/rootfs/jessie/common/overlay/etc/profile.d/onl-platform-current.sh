############################################################
#
# Add platform specific directories to path.
#
############################################################
dir=/lib/platform-config/current/onl
export PATH="$PATH:$dir/bin:$dir/sbin:$dir/lib/bin:$dir/lib/sbin"


#################################################
#sole for wedge100bf
#################################################
depmod
modprobe accton_wedge100bf_psensor model_id=1

ifconfig usb0 up
. /usr/local/barefoot/sbin/setup_switch.sh

# double '&' to make it daemon, redirect stdout to avoid printing prompt.
alias run_bf_bg='(bf_switchd --install-dir /usr/local/barefoot --conf-file /usr/local/barefoot/share/p4/targets/tofino/diag.conf --status-port 7777 --background 1> /dev/null &)&'

run_bf_bg
#clear cache file
onlp_sfp_poll.py clean
