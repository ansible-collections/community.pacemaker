#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Rhys Campbell (@rhysmeister) <rhyscampbell@bluewin.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pacemaker_cluster

short_description: Manage a Pacemaker Cluster and the nodes within it..

description:
  - Manage a Pacemaker Cluster and the nodes within it.
  - Manages the /etc/corosync/corosync.conf file either directly or through pcs cluster commands.

author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.pacemaker.pacemaker_options

options:
  members:
    description:
      - Hosts in the .
      - Required when I(state=present).
    type: list
    elements: str
    aliases:
      - hosts
  state:
    description:
      - The desired state of the Pacemaker Cluster.
      - The cluster must be started for most operations to succeed.
    type: str
    choices:
      - "started"
      - "stopped"
    default: "started"
  corosync_file:
    description:
      - Path to the corosync configuration file.
    type: str
    default: /etc/corosync/corosync.conf
  name:
    description:
      - Name of the cluster.
      - Note that the cluster name will only be set upon cluster creation.
      - To rename a cluster see the following guide https://access.redhat.com/solutions/2160321
      - Attempting to perform any operation on a cluster with a different name will fail.
    type: str
    required: yes
    aliases:
      - cluster
      - cluster_name
  enabled:
    description:
      - Enable the Pacemaker Cluster on the node.
    type: bool
    default: false
  wait:
    description:
      - Wait up to 'n' seconds for the nodes to start
    type: int
    aliases:
      - timeout
  local:
    description:
      - Execute cmd with the --local flag.
      - Only perform auth on the local node.
    type: bool
    default: false

notes:
    - Requires the pcs utility on the remote host.
'''

EXAMPLES = r'''
- name: Setup cluster
  community.pacemaker.pacemaker_cluster:
    members:
      - amazonlinux1.pacemaker
      - amazonlinux2.pacemaker
      - amazonlinux3.pacemaker
    state: "started"
    enabled: yes
    name: AMZ
'''

RETURN = r'''
changed:
  description: If the module caused a change.
  returned: on success
  type: bool
msg:
  description: Status message.
  returned: always
  type: str
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

from ansible_collections.community.pacemaker.plugins.module_utils.pacemaker_options import (
    pacemaker_common_argument_spec
)

from ansible_collections.community.pacemaker.plugins.module_utils.pacemaker_common import (
    file_exists,
    build_cluster_setup_cmd,
    get_cluster_name
)

import traceback


def main():
    argument_spec = pacemaker_common_argument_spec()
    argument_spec.update(
        members=dict(type='list', elements='str', aliases=["hosts"]),
        state=dict(type='str', choices=["started", "stopped"], default="started"),
        corosync_file=dict(type='str', default="/etc/corosync/corosync.conf"),
        name=dict(type='str', required=True, aliases=["cluster", "cluster_name"]),
        enabled=dict(type='bool', default=False),
        wait=dict(type='int', default=None, aliases=["timeout"]),
        local=dict(type='bool', default=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    rc, out, err = None, None, None
    result = {}
    state = module.params["state"]
    corosync_file = module.params["corosync_file"]
    if state == "present" and module.params['members'] is None:
        module.fail_json(msg="members parameter is required when state is present")

    try:
        result = {}
        rc, out, err = None, None, None
        corosync_file_exists = file_exists(corosync_file)
        if corosync_file_exists:
            current_cluster_name = get_cluster_name()
            if current_cluster_name != module.params["name"]:
                module.fail_json(msg="The expected cluster name is {0} but {1} was found".format(module.params['name'], current_cluster_name))
        rc, out, err = module.run_command("pcs status")
        cluster_started = None
        cluster_enabled = None

        if rc == 0:  # assume cluster is started
            cluster_started = True
            if "corosync: active/enabled" in out\
                    and "pacemaker: active/enabled" in out\
                    and "pcsd: active/enabled" in out:
                cluster_enabled = True
            else:
                cluster_enabled = False
        else:
            cluster_started = False

        pcsd_status = None
        rc, out, err = module.run_command("pcs cluster status")
        if rc == 0:
            pcsd_status = True
        else:
            pcsd_status = False

        if state == "started":
            if pcsd_status:  # nodes are configured
                pass
            else:
                setup_cluster_cmd = build_cluster_setup_cmd(module, module.params['members'])
                if module.params["debug"]:
                    result["cmd"] = setup_cluster_cmd
                if module.check_mode is False:
                    rc, out, err = module.run_command(setup_cluster_cmd)
                if rc != 0:
                    if module.params['debug']:
                        result["err"] = err
                        result["out"] = out
                    module.fail_json(msg="Failed creating cluster rc = {0}".format(rc), **result)
                result["changed"] = True
                result["msg"] = "The cluster {0} was created successfully".format(module.params['name'])
        elif state == "stopped":
            if cluster_started:
                if module.check_mode is False:
                    rc, out, err = module.run_command("{0} cluster stop --all".format(module.params['pcs_util']))
                if rc != 0:
                    module.fail_json(msg="Failed stopping cluster rc = {0}".format(rc))
                result["changed"] = True
                result["msg"] = "Successfully stopped cluster"
            else:
                result["changed"] = False
                result["msg"] = "Cluster is not running"

        if module.params['debug']:
            if rc is not None:
                result["rc"] = rc
            if out is not None:
                result["out"] = out
            if err is not None:
                result["out"] = out

    except Exception as excep:
        if module.params["debug"]:
            excep = traceback.format_exc()
        module.fail_json(msg='Error: %s' % to_native(excep))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
