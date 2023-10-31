#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Rhys Campbell (@rhysmeister) <rhyscampbell@bluewin.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pacemaker_property

short_description: Manage Pacemaker Cluster Properties.

description:
  - Manage Pacemaker Cluster Properties.

author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.pacemaker.pacemaker_options

options:
  property_name:
    description:
      - The property to manage.
    type: str
  property_value:
    description:
      - The desired value of the propery
      - All values should be quoted to prevent Ansible munging the data type.\
        For example yaml boolean would be transformed by Ansible into False and\
        the following error would result "invalid property format: 'False'".
    type: str
  state:
    description:
      - The desired state of the property.
    type: str
    choices:
      - "present"
      - "absent"
      - "default"
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
- name: Only ever turn fencing off on a test cluster
  community.pacemaker.pacemaker_property:
    property_name: "stonith-enabled"
    property_value: false
    state: "present"

- name: Set a property to default
  community.pacemaker.pacemaker_property:
    property_name: "symmetic-cluster"
    state: "default"
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

# TODO Refactor to common code and add unit tests
def show_property(module, default):
    cluster_properties = {}
    flag = "all"
    if default:
        flag = "default"
    cmd = "{0} property list --{1}".format(module.params['pcs_util'], flag)
    (rc, out, err) = module.run_command(cmd)
    if rc != 0:
        module.fail_json(msg="Failed listing cluster properties: {0}".format(err))
    else:
        k, v = None, None
        try:
            for line in out.split('\n'):
                if line.startswith('Cluster Properties') is False:
                    if len(line.split(':')) == 2:
                        k, v = line.split(':')
                    elif module.params['debug']:
                        module.warn("Incorrect number of values from line: {0}".format(line))
                    cluster_properties[k.strip()] = v.strip()
        except Exception as e:
            if module.params['debug']:
                module.fail_json(msg="Failed parsing cluster properties: {0}, {1}, Current kv pair: {2} {3}".format(e, cluster_properties, k, v))
            module.fail_json(msg="Failed parsing cluster properties: {0}".format(e))
    return cluster_properties[module.params.get('property_name', None)]


def set_property(module, default):
    cmd = "{0} property set {1}=".format(module.params['pcs_util'],
                                         module.params['property_name'])
    if default is False:
        cmd = "{0}{1}".format(cmd, module.params['property_value'])
    (rc, out, err) = module.run_command(cmd)
    if rc != 0:
        module.fail_json(msg="Failed setting cluster property: {0}".format(err))
    return True


def unset_property(module):
    cmd = "{0} property unset {1}".format(module.params['pcs_util'],
                                          module.params['property_name'])
    (rc, out, err) = module.run_command(cmd)
    if rc != 0:
        module.fail_json(msg="Failed unsetting cluster property: {0}".format(err))
    return True

def is_property_defined(module):
    cmd = " {0} property show {1}".format(module.params['pcs_util'],
                                          module.params['property_name'])
    (rc, out, err) = module.run_command(cmd)
    if rc != 0:
        module.fail_json(msg="Failed checking cluster property: {0}".format(err))
    if module.params['property_name'] in out:
        return True
    else:
        return False



def main():
    argument_spec = pacemaker_common_argument_spec()
    argument_spec.update(
        property_name=dict(type='str'),
        property_value=dict(type='str'),
        state=dict(type='str', choices=["present", "absent", "default"], default="present"),
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
        result = {}
        current_value = show_property(module, False)
        if state == "present":
            if current_value == module.params['property_value']:
                result['changed'] = False
                result['msg'] = "{0} is already set to {1}".format(module.params['property_name'],
                                                                   module.params['property_value'])
            else:
                if module.check_mode is False:
                    set_property(module, False)
                result['changed'] = True
                result['msg'] = "{0} has been set to {1}".format(module.params['property_name'],
                                                                   module.params['property_value'])
        elif state == "absent":
            if is_property_defined(module) is False:
                result['changed'] = False
                result['msg'] = "{0} is not set in the cluster configuration".format(module.params['property_name'])
            else:
                if module.check_mode is False:
                    unset_property(module)
                result['changed'] = True
                result['msg'] = "{0} has been unset in the cluster configuration".format(module.params['property_name'])
        elif state == "default":
            default_value = show_property(module, True)
            if default_value == current_value:
                result['changed'] = False
                result['msg'] = "{0} is already set to the default: {1}".format(module.params['property_name'],
                                                                                default_value)
            else:
                if module.check_mode is False:
                    set_property(module, True)
                result['changed'] = True
                result['msg'] = "{0} has been set to the default: {1}".format(module.params['property_name'],
                                                                              default_value)
    except Exception as excep:
        if module.params["debug"]:
            excep = traceback.format_exc()
        module.fail_json(msg='Error: %s' % to_native(excep))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
