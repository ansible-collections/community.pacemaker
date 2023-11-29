#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Rhys Campbell (@rhysmeister) <rhyscampbell@bluewin.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pacemaker_constraint

short_description: Manage Constraints for a Pacemaker Cluster.

description:
  - Manage Constraints for a Pacemaker Cluster.
  - At the moment this module will only create or remove the constraint
  - Verification is performed by name only.
  - This module is very simple and will likely not support advanced constraint configurations.

author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.pacemaker.pacemaker_options

options:
  name:
    description:
      - The id of the constraint.
      - By convention this should be the resource name, or group
      - Note that a unique id with the type will be created, e.g. <name>_<type>.
      - Example, when name is httpd and the constraint type is location the id will be httpd_location.
    type: str
    aliases:
      - constraint_name
    required: true
  type:
    description:
      - The type of constraint.
    type: str
    choices:
      - location
      - order
      - colocation
    aliases:
      - constraint_type
  prefers:
    description:
      - Used when the constraint type is location.
      - Specify which nodes a resource is prefered to run on.
      - Mutually exclusive with avoids.
    type: list
    elements: raw
  avoids:
    description:
      - Used when the constraint type is location.
      - Specifiy which nodes a resource should avoid.
      - Mutually exclusive with prefers.
    type: list
    elements: raw
  order:
    description:
      - Used when the constraint type is order.
      - Specify in which order resources should be started, stopped or otherwise managed.
      - Mutually exclusive with set.
    type: list
    elements: raw
  set:
     description:
      - Used when the constraint type is order.
      - Create a chain of ordered resources.
      - Mutually exclusive with order.
     type: list
     elements: str
  resources:
    description:
      - Used when the constraint type is colocation.
      - Specifiy which resources should be colocated.
    type: list
    elements: raw
  state:
    description:
      - The desired state of the constraint.
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
- name: Create a location constraint
  community.pacemaker.pacemaker_constraint:
    name: myResource
    type: location
    prefers:
      - node1: 100

- name: INFINITY score means never run on that node
  community.pacemaker.pacemaker_constraint:
    name: myResource
    type: location
    avoids:
      - node5: INFINITY

- name: Start resources in a specific order
  community.pacemaker.pacemaker_constraint:
    name: startResources
    type: order
    order:
      - start: mounts
      - start: mysql
      - start: httpd

- name: Stop resources in a specific order
  community.pacemaker.pacemaker_constraint:
    name: stopResources
    type: order
    order:
      - stop: httpd
      - stop: mysql
      - stop: mounts

- name: Create an ordered set of resources
  community.pacemaker.pacemaker_constraint:
    name: resourceSet
    type: order
    set:
      - mounts
      - mysql
      - httpd

- name: Colocate resources
  community.pacemaker.pacemaker_constraint:
    name: myResource
    type: colocation
    resources:
      - httpd
      - mysql

- name: Remove a constraint
  community.pacemaker.pacemaker_constraint:
    name: myResource
    state: absent
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

def get_constraint_id(module):
    """
    Returns the constraint id that we always want this module to create/manage.
    TODO - We need to change this is, it is not unique
    """
    return "{0}_{1}".format(module.params['name'], module.params['type'])


def is_constraint_configured(module):
    """
    Returns true if the given constraint is configured.
    We only check the name of the constraint. Configuration
    is not checked at all.
    """
    status = False
    cmd = "{0} constraint show --full".format(module.params['pcs_util'])
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        if get_constraint_id(module) in out:
            status = True
    else:
        module.fail_json(msg="Failed checking constraint: {0}".format(err + " : " + out))
    return status


def delete_constraint(module):
    """
    Returns true if the constraint was deleted
    """
    id = get_constraint_id(module)
    status = False
    cmd = "{0} constraint remove {1}".format(module.params['pcs_util'], id)
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        status = True
    else:
        module.fail_json(msg="Failed to delete the constraint {0}: {1}".format(id, err))
    return status


def create_constraint(module):
    """
    This function creates the constraint by first building the appropriate command.
    pcs provides a huge amount of richness when it comes to configuraing constraints.
    We should not attempt to support them all, just the basic use cases.
    """
    status = False  # Have we been successful?
    id = get_constraint_id(module)
    constraint_type = module.params['type']
    cmd = "{0} constraint {1} add {2} {3}".format(module.params['pcs_util'],
                                                  constraint_type,
                                                  id,
                                                  module.params['name'])
    if constraint_type == "location":
        # These two commands are supposed to work with multiple nodes but don't seem to... perhaps a version thing?
        # Had to remove the prefers and avoids keywords... these are documented in the help for v0.9.169 but don't seem to work
        # revisit this when we upgrade to a newer version?
        if module.params['prefers'] is not None:
            node_config = ' '.join(["{} {}".format(key, value) for d in module.params['prefers'] for key, value in d.items()]).strip()
            cmd = "{0} {1}".format(cmd, node_config)
        elif module.params['avoids'] is not None:
            # The minus turns it into an avoid
            node_config = ' '.join(["{} -{}".format(key, value) for d in module.params['avoids'] for key, value in d.items()]).strip()
            cmd = "{0} {1}".format(cmd, node_config)
        else:
            module.fail_json(msg="invalid verb with location constraint")
    elif constraint_type == "order":
        if module.params['order'] is not None:
            res = module.params['order']  # limited to 2 resources
            r1_action = list(res[0].keys())[0]
            r1_name = res[0][r1_action]
            r2_action = list(res[1].keys())[0]
            r2_name = res[1][r1_action]
            cmd = "{0} constraint order".format(module.params['pcs_util'])
            cmd = "{0} {1}".format(cmd, "{} {} then {} {}".format(r1_action, r1_name, r2_action, r2_name))
            cmd = "{0} id={1}".format(cmd, id)
        elif module.params['set']:
            cmd = "{0} constraint {1} set {2} id={3}".format(module.params['pcs_util'],
                                                             constraint_type,
                                                             " ".join(resource for resource in module.params['set']),
                                                             id)
        else:
            module.fail_json(msg="either the order or set config keys must be provided when type is order")
    elif constraint_type == "colocation":
        if module.params['resources']:
            cmd = "{0} {1}".format(cmd, " with ".join(resource for resource in module.params['resources']))
        else:
            module.fail_json(msg="the resources config key must be provided when type is order")

    # Execute the cmd and set status to True if successful
    rc, out, stderr = module.run_command(cmd)
    if module.params['debug']:
        module.warn(cmd)  # TODO clean this up
        module.warn(out)
        module.warn(stderr)
    if rc == 0:
        status = True
    return status


def main():
    argument_spec = pacemaker_common_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
        type=dict(type='str', choices=["location", "order", "colocation"]),
        prefers=dict(type='list', elements='raw'),
        avoids=dict(type='list', elements='raw'),
        order=dict(type='list', elements='raw'),
        set=dict(type='list', elemets='str'),
        resources=dict(type='list', elemets='str'),
        state=dict(type='str', choices=["present", "absent"], default="present"),
        local=dict(type='bool', default=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    result = {}
    state = module.params["state"]

    if len(module.params['order'] or []) > 2:
        module.fail_json(msg="Use the 'pcs constraint order set' command if you want to create a constraint for more than two resources.")

    try:
        constraint_id = get_constraint_id(module)
        exists = is_constraint_configured(module)

        if state == "present":
            if exists:
                result['changed'] = False
                result['msg'] ="The constraint {0} already exists".format(constraint_id)
            else:
                if module.check_mode is False:
                    create_constraint(module)
                result['changed'] = True
                result['msg'] = "The constraint {0} was successfully created".format(constraint_id)
        elif state == "absent":
            if exists:
                if module.check_mode is False:
                    delete_constraint(module)
                result['changed'] = True
                result['msg'] = "The constraint {0} was successfully deleted".format(constraint_id)
            else:
                result['changed'] = False
                result['msg'] = "The constraint {0} does not exist".format(constraint_id)
    except Exception as excep:
        if module.params["debug"]:
            excep = traceback.format_exc()
        module.fail_json(msg='Error: %s' % to_native(excep))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
