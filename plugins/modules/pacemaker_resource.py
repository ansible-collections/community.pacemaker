#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Rhys Campbell (@rhysmeister) <rhyscampbell@bluewin.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pacemaker_resource

short_description: Create and manage resources within a Pacemaker cluster.

description:
  - Create and manage resources within a Pacemaker cluster.
  - This module does not check resource configuration for changes.
  - To update a resource you can delete it before recreating.

author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.pacemaker.pacemaker_options

options:
  resource_name:
    description:
      - The name of the resource.
    type: str
    required: true
  resource_type:
    description:
      - The type of resource.
      - Required when state is present
    type: str
  resource_config:
    description:
      - The configuration of the resource.
      - Supply as key value pairs.
      - Required when state is present.
    type: dict
  resource_group:
    description:
      - The group to add the resource to.
      - Will be created if it does not exist.
    type: str
  state:
    description:
      - The desired state of the Pacemaker resource.
    type: str
    choices:
      - "present"
      - "absent"
      - "enabled"
      - "disabled"
      - "move"
      - "debug-start"
    default: "present"
  member:
    description:
      - Member nominated for the move command.
      - Required when status is move.
    type: str
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
- name: Create myFS resource
  community.pacemaker.pacemaker_resource:
    resource_name: myFS
    resource_type: FileSystem
    resource_config:
      device: 'nfs_server:/export/www'
      directory: '/www'
      fstype: 'nfs'
    resource_group: apache
    state: present

- name: Create floating ip resource
  community.pacemaker.pacemaker_resource:
    resource_name: ClusterIP
    resource_type: ocf:heartbeat:apache
    resource_config:
      ip: 192.168.122.120
    resource_group: apache
    state: present

- name: Create website
  community.pacemaker.pacemaker_resource:
    resource_name: website
    resource_type: ocf:heartbeat:apache
    resource_config:
      configfile: /etc/httpd/conf/httpd.conf
      statusurl: "http://localhost/server-status"
    resource_group: apache
    state: present

- name: Delete a resource
  community.pacemaker.pacemaker_resource:
    resource_name: website
    state: absent

- name: Move myFS resource
  community.pacemaker.pacemaker_resource:
    resource_name: myFS
    resource_type: FileSystem
    state: "move"
    member: pacemaker-2
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
    get_cluster_resources
)

import traceback


def main():
    argument_spec = pacemaker_common_argument_spec()
    argument_spec.update(
        resource_name=dict(type='str', required=True),
        resource_type=dict(type='str'),
        resource_config=dict(type='dict'),
        resource_group=dict(type='str'),
        state=dict(type='str', choices=["present", "absent", "enabled", "disabled", "move", "debug-start"], default="present"),
        member=dict(type='str'),
        local=dict(type='bool', default=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    rc, out, err = None, None, None
    result = {}
    state = module.params["state"]

    if state == "present" and (module.params['resource_type'] is None or module.params['resource_config'] is None):
        module.fail_json(msg="resource_type and resource_config parameters are required when state is present")
    if state == "move" and module.params['member'] is None:
        module.fail_json(msg="The member parameter is required when state is move")

    try:
        result = {}
        rc, out, err = None, None, None
        myResource = None

        # Get cluster resource
        resources = get_cluster_resources(module, None)
        # module.warn(str(resources))
        for resource in resources:
            if resource['resource_name'] == module.params['resource_name']:
                myResource = resource

        # TODO Refector this code
        if state == "present":
            if myResource is None:
                cmd = "{0} resource create {1} {2} ".format(module.params["pcs_util"],
                                                            module.params['resource_name'],
                                                            module.params['resource_type'])
                for k, v in module.params['resource_config'].items():
                    cmd += "{0}={1} ".format(k, v)
                if module.params['resource_group'] is not None:
                    cmd = "{0} --group {1}".format(cmd, module.params['resource_group'])
                if module.check_mode is False:
                    rc, out, err = module.run_command(cmd)
                    if rc != 0:
                        module.warn(str(myResource))
                        module.fail_json(msg="Failed creating the resource {0}: {1}".format(module.params['resource_name'],
                                                                                            err))
                result["changed"] = True
                result["msg"] = "Successfully created the resource {0}".format(module.params['resource_name'])
            else:
                module.exit_json(changed=False, msg="The resource {0} already exists in the cluster".format(module.params['resource_name']))
        elif state == "absent":
            if myResource is None:
                module.exit_json(changed=False, msg="The resource {0} does not exist in the cluster".format(module.params['resource_name']))
            else:
                cmd = "{0} resource delete {1}".format(module.params["pcs_util"],
                                                       myResource['resource_name'])
                if module.check_mode is False:
                    rc, out, err = module.run_command(cmd)
                    if rc != 0:
                        module.fail_json(msg="failed deleting the resource {0}: {1}".format(myResource['resource_name'],
                                                                                            err))
                result["changed"] = True
                result["msg"] = "The resource {0} was deleted from the cluster".format(myResource['resource_name'])
        elif state == "enabled":
            cmd = "{0} resource enable {1}".format(module.params["pcs_util"],
                                                   myResource['resource_name'])
            module.fail_json(msg="This feature is not yet implemented")
        elif state == "disabled":
            cmd = "{0} resource disable {1}".format(module.params["pcs_util"],
                                                    myResource['resource_name'])
            module.fail_json(msg="This feature is not yet implemented")
        elif state == "move":
            cmd = "{0} resource move {1} {2}".format(module.params["pcs_util"],
                                                     myResource['resource_name'],
                                                     module.params['member'])
            if module.check_mode is False:
                rc, out, err = module.run_command(cmd)
                if rc != 0:
                    module.fail_json(msg="failed starting the resource {0}: {1}".format(myResource['resource_name'],
                                                                                        err))
            result["changed"] = True
            result["msg"] = "The resource {0} has been moved".format(myResource['resource_name'])
        elif state == "debug-start":
            if myResource["resource_state"] == "Stopped":
                cmd = "{0} resource debug-start {1}".format(module.params["pcs_util"],
                                                            myResource['resource_name'])
                if module.check_mode is False:
                    rc, out, err = module.run_command(cmd)
                    if rc != 0:
                        module.fail_json(msg="failed starting the resource {0} in debug mode: {1}".format(myResource['resource_name'],
                                                                                                          err))
                result["changed"] = True
                result["msg"] = "The resource {0} has been started in debug mode".format(myResource['resource_name'])
            else:
                result["changed"] = False
                msg = "The resource {0} is already started. Stop the resource first before starting it in debug mode"
                result["msg"] = msg.format(myResource['resource_name'])

    except Exception as excep:
        if module.params["debug"]:
            excep = traceback.format_exc()
        module.fail_json(msg='Error: %s' % to_native(excep))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
