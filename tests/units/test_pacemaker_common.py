from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import unittest
import pathlib
import os
import sys
import json

path = os.path.dirname(os.path.realpath(__file__))
path = "{0}/../../plugins/module_utils".format(path)
sys.path.append(path)
import pacemaker_common

data = {
            "format_version": 3,
            "data_version": 2,
            "tokens": {
                "amazonlinux1.pacemaker": "bff36ce9-13f4-4589-943e-dfaea6c3d98c",
                "amazonlinux2.pacemaker": "28287431-4879-47bd-96d3-6a07726820a2",
                "amazonlinux3.pacemaker": "c9f46b63-85b7-4438-860b-54019e55745b"
            },
            "ports": {
                "amazonlinux1.pacemaker": 2224,
                "amazonlinux2.pacemaker": 2224,
                "amazonlinux3.pacemaker": 2224
            }
        }

corosync_data = """
# Please read the corosync.conf.5 manual page
totem {
    version: 2

    # Corosync itself works without a cluster name, but DLM needs one.
    # The cluster name is also written into the VG metadata of newly
    # created shared LVM volume groups, if lvmlockd uses DLM locking.
    # It is also used for computing mcastaddr, unless overridden below.
    cluster_name: debian

    # How long before declaring a token lost (ms)
    token: 3000

    # How many token retransmits before forming a new configuration
    token_retransmits_before_loss_const: 10

    # Limit generated nodeids to 31-bits (positive signed integers)
    clear_node_high_bit: yes

    # crypto_cipher and crypto_hash: Used for mutual node authentication.
    # If you choose to enable this, then do remember to create a shared
    # secret with "corosync-keygen".
    # enabling crypto_cipher, requires also enabling of crypto_hash.
    # crypto_cipher and crypto_hash should be used instead of deprecated
    # secauth parameter.

    # Valid values for crypto_cipher are none (no encryption), aes256, aes192,
    # aes128 and  3des. Enabling crypto_cipher, requires also enabling of
    # crypto_hash.
    crypto_cipher: none

    # Valid values for crypto_hash are  none  (no  authentication),  md5,  sha1,
    # sha256, sha384 and sha512.
    crypto_hash: none

    # Optionally assign a fixed node id (integer)
    # nodeid: 1234

    # interface: define at least one interface to communicate
    # over. If you define more than one interface stanza, you must
    # also set rrp_mode.
    interface {
        # Rings must be consecutively numbered, starting at 0.
        ringnumber: 0
        # This is normally the *network* address of the
        # interface to bind to. This ensures that you can use
        # identical instances of this configuration file
        # across all your cluster nodes, without having to
        # modify this option.
        bindnetaddr: 127.0.0.1
        # However, if you have multiple physical network
        # interfaces configured for the same subnet, then the
        # network address alone is not sufficient to identify
        # the interface Corosync should bind to. In that case,
        # configure the *host* address of the interface
        # instead:
        # bindnetaddr: 192.168.1.1
        # When selecting a multicast address, consider RFC
        # 2365 (which, among other things, specifies that
        # 239.255.x.x addresses are left to the discretion of
        # the network administrator). Do not reuse multicast
        # addresses across multiple Corosync clusters sharing
        # the same network.
        # mcastaddr: 239.255.1.1
        # Corosync uses the port you specify here for UDP
        # messaging, and also the immediately preceding
        # port. Thus if you set this to 5405, Corosync sends
        # messages over UDP ports 5405 and 5404.
        mcastport: 5405
        # Time-to-live for cluster communication packets. The
        # number of hops (routers) that this ring will allow
        # itself to pass. Note that multicast routing must be
        # specifically enabled on most network routers.
        ttl: 1
    }
}

logging {
    # Log the source file and line where messages are being
    # generated. When in doubt, leave off. Potentially useful for
    # debugging.
    fileline: off
    # Log to standard error. When in doubt, set to no. Useful when
    # running in the foreground (when invoking "corosync -f")
    to_stderr: no
    # Log to a log file. When set to "no", the "logfile" option
    # must not be set.
    to_logfile: no
    #logfile: /var/log/corosync/corosync.log
    # Log to the system log daemon. When in doubt, set to yes.
    to_syslog: yes
    # Log with syslog facility daemon.
    syslog_facility: daemon
    # Log debug messages (very verbose). When in doubt, leave off.
    debug: off
    # Log messages with time stamps. When in doubt, set to on
    # (unless you are only logging to syslog, where double
    # timestamps can be annoying).
    timestamp: on
    logger_subsys {
        subsys: QUORUM
        debug: off
    }
}

quorum {
    # Enable and configure quorum subsystem (default: off)
    # see also corosync.conf.5 and votequorum.5
    provider: corosync_votequorum
    expected_votes: 2
}
"""


class TestPacemakerCommonMethods(unittest.TestCase):

    def test_file_exists(self):
        test_file = "/tmp/random_file_4nbdcfgsadfuarz23r.txt"
        pathlib.Path(test_file).touch()
        self.assertTrue(pacemaker_common.file_exists(test_file))
        os.remove(test_file)
        self.assertFalse(pacemaker_common.file_exists(test_file))

    def test_get_json_file(self):
        test_file = '/tmp/json_data_sdfsdfg67345rgdcy.json'
        with open(test_file, 'w') as json_file:
            json.dump(data, json_file)
        self.assertTrue(pacemaker_common.get_json_file(test_file))
        os.remove(test_file)

    def test_valid_pcsd_tokens_data(self):
        self.assertTrue(pacemaker_common.valid_pcsd_tokens_data(data))
        self.assertFalse(pacemaker_common.valid_pcsd_tokens_data({"invalid_structure": True}))

    def test_pcsd_tokens_file(self):
        self.assertTrue(pacemaker_common.pcsd_tokens_file(user="root") == "/var/lib/pcsd/tokens")
        self.assertTrue(pacemaker_common.pcsd_tokens_file(user="notroot") == "~/.pcs/tokens")
        # default os user for ansible-test is pytest
        self.assertTrue(pacemaker_common.pcsd_tokens_file() == "~/.pcs/tokens")

    def test_build_cluster_auth_cmd_test1(self):

        class FakeAnsinbleModule:

            params = {
                "pcs_util": "pcs",
                "username": "hacluster",
                "password": "mysecretpassword",
                "local": True,
                "force": True,
            }

            def __init__(self):
                self.msg = ""
                self.warning = ""

        module = FakeAnsinbleModule()
        members_without_port = ["server1", "server2", "server3"]
        port = None
        cmd = pacemaker_common.build_cluster_auth_cmd(module, members_without_port, port)
        self.assertTrue(cmd.startswith("pcs cluster auth"))
        self.assertTrue("server1" in cmd)
        self.assertTrue("server2" in cmd)
        self.assertTrue("server3" in cmd)
        self.assertTrue("--local" in cmd)
        self.assertTrue("--force" in cmd)
        self.assertTrue(":" not in cmd)
        self.assertTrue("hacluster" in cmd)
        self.assertTrue("mysecretpassword" in cmd)

    def test_build_cluster_auth_cmd_test2(self):

        class FakeAnsinbleModule:

            params = {
                "pcs_util": "/usr/bin/pcs",
                "username": "hacluster",
                "password": "mysecretpassword",
                "local": False,
                "force": False,
            }

            def __init__(self):
                self.msg = ""
                self.warning = ""

        module = FakeAnsinbleModule()
        members_without_port = ["server1", "server2", "server3"]
        port = 1234
        cmd = pacemaker_common.build_cluster_auth_cmd(module, members_without_port, port)
        self.assertTrue(cmd.startswith("/usr/bin/pcs cluster auth"))
        self.assertTrue("server1" in cmd)
        self.assertTrue("server2" in cmd)
        self.assertTrue("server3" in cmd)
        self.assertTrue("--local" not in cmd)
        self.assertTrue("--force" not in cmd)
        self.assertTrue(":1234" in cmd)
        self.assertTrue("hacluster" in cmd)
        self.assertTrue("mysecretpassword" in cmd)

    def test_build_cluster_setup_cmd_test1(self):

        class FakeAnsinbleModule:

            params = {
                "pcs_util": "pcs",
                "local": True,
                "force": True,
                "name": "debian",
                "state": "started",
                "enabled": True,
                "wait": None
            }

            def __init__(self):
                self.msg = ""
                self.warning = ""

        module = FakeAnsinbleModule()
        members_without_port = ["server1", "server2", "server3"]
        cmd = pacemaker_common.build_cluster_setup_cmd(module, members_without_port)
        self.assertTrue(cmd.startswith("pcs cluster setup"))
        self.assertTrue("server1" in cmd)
        self.assertTrue("server2" in cmd)
        self.assertTrue("server3" in cmd)
        self.assertTrue("--local" in cmd)
        self.assertTrue("--force" in cmd)
        self.assertTrue("--start" in cmd)
        self.assertTrue("--enable" in cmd)
        self.assertTrue("--name" in cmd)

    def test_get_cluster_name(self):
        corosync_file = "/tmp/corosync.conf.test.1hcsdf6wq4rghbsdjc"
        with open(corosync_file, "w") as file:
            file.write(corosync_data)
        cluster_name = pacemaker_common.get_cluster_name(corosync_file=corosync_file)
        self.assertTrue(cluster_name == "debian")
