#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Rhys Campbell (@rhysmeister) <rhyscampbell@bluewin.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pacemaker_fance

short_description: Manage Fences for a Pacemaker Cluster.

description:
  - Manage Manage Fences for a Pacemaker Cluster.
  - At the moment this module will only create or remove the fence.
  - Verification is performed by name only.

author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.pacemaker.pacemaker_options

options:
  name:
    description:
      - The name of the fence to manage.
    type: str
    aliases:
      - fence_name
    required: true
  agent:
    description:
      - The  fence agent to use.
    type: str
    aliases:
      - fence_agent
  config:
    description:
      - The configuration of the fence agent.
      - There is no restriction on the values you provide here.
      - Acceptable values are dependent on the Fence Agent and this module has no knowledge of them.
      - Run the command `pcs stonith describe <fence agent>` to see these options.
    type: dict
    aliases:
      - fence_config
  state:
    description:
      - The desired state of the property.
    type: str
    choices:
      - "present"
      - "absent"
    default: "present"
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
- name: Create a fence
  community.pacemaker.pacemaker_fence:
    name: "{{ inventory_hostname }}"
    agent: "fence_vbox"
    config:
      ipddr: "192.168.1.101"
      login: "rhys"
      pcmk_host_list: "{{ inventory_hostname }}"
      identity_file: "/path/to/id_rsa"

- name: Remove a fence
  community.pacemaker.pacemaker_fence:
    name: "{{ inventory_hostname }}"
    state: "absent"
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

import traceback

# TODO Refactor to common and add unit tests?

"""
Return true of the fencing agent exists on the host
"""
def fence_agent_exists(module):
    status = False
    cmd = "{0} stonith describe {1}".format(module.params['pcs_util'],
                                            module.params['agent'])
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        status = True
    return status

"""
Returns true if the given fence is configured.
We only check the name of the fence. Configuration
is not checked at all.
"""
def is_fence_configured(module):
    status = False
    cmd = "{0} stonith show {1}".format(module.params['pcs_util'],
                                        module.params['name'])
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        status = True
    return status

"""
Returns true if the fence was deleted
"""
def delete_fence(module):
    status = False
    cmd = "{0} stonith delete {1}".format(module.params['pcs_util'],
                                          module.params['name'])
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        status = True
    else:
        module.fail_json(msg="Failed to delete the fence {0}: {1}".format(module.params['name'],
                                                                          err))
    return status

def create_fence(module):
    options = ''.join(["{0}={1} ".format(k, v) for k, v in module.params['config'].items()])
    cmd = "{0} stonith create {1} {2} {3}".format(module.params['pcs_util'],
                                                  module.params['name'],
                                                  module.params['agent'],
                                                  options)
    module.warn(str(cmd))
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        status = True
    else:
        module.fail_json(msg="Failed creating the fence {0}: {1}".format(module.params['name'],
                                                                         err + " : " + out))
    return status


def main():
    argument_spec = pacemaker_common_argument_spec()
    argument_spec.update(
        name=dict(type='str', aliases=["fence_name"], required=True),
        agent=dict(type='str', aliases=["fence_agent"]),
        config=dict(type='dict', aliases=["fence_config"]),
        state=dict(type='str', choices=["present", "absent"], default="present"),
        local=dict(type='bool', default=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    rc, out, err = None, None, None
    result = {}
    state = module.params["state"]

    try:
        if state == "present" and fence_agent_exists(module) is False:
            module.fail_json(msg="The configured fence agent does not exist: {0}".format(module.params['agent']))
        result = {}
        fence_exists = is_fence_configured(module)

        if state == "present":
            if fence_exists:
                module.exit_json(changed=False, msg="The fence {0} already exists".format(module.params['name']))
            else:
                if module.check_mode is False:
                    create_fence(module)
                module.exit_json(changed=True, msg="The fence {0} was successfully created".format(module.params['name']))
        elif state == "absent":
            if fence_exists is False:
                module.exit_json(changed=False, msg="The fence {0} does not exist".format(module.params['name']))
            else:
                if module.check_mode is False:
                    delete_fence(module)
                module.exit_json(changed=True, msg="The fence {0} was successfully deleted".format(module.params['name']))
    except Exception as excep:
        if module.params["debug"]:
            excep = traceback.format_exc()
        module.fail_json(msg='Error: %s' % to_native(excep))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
