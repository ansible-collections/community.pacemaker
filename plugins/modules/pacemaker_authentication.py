#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Rhys Campbell (@rhysmeister) <rhyscampbell@bluewin.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pacemaker_authentication

short_description: Authenticate pcs to pcsd on nodes specified.

description:
  - Manages the pcs tokens file either directly or through pcs auth commands.
  - Authenticate pcs to pcsd on nodes specified.
  - Tokens are stored in /var/lib/pcsd/tokens for root or ~/.pcs/tokens for other users.
  - Using the local parameter only authenticates the local node but by default all nodes are authenticated to each other.
  - Using the force parameter forces re-authentication to occur.
  - Supports removal of hosts from the pcsd tokens file. We simply remove the data. No other action is performed.
  - It's possible the module could be non-atomic when adding new and removing members at the same time.\
    Perform these actions individually to minimise that risk.

author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.pacemaker.pacemaker_options

options:
  members:
    description:
      - Hosts to authenticate between.
      - Required when I(state=present).
    type: list
    elements: str
    aliases:
      - hosts
  state:
    description:
      - The desired state of the members in the pcsd token file.
      - When the state is set to "present" the tokens file is synced to the members list,\
        i.e. hosts are added or removed. When adding hosts are authenticated in order to get a token.\
        When removing hosts we only remove the data from the pcsd tokens file.
      - When the state is set to "absent" we will delete the tokens file.
    type: str
    choices:
      - "present"
      - "absent"
    default: "present"
  pcsd_tokens_file:
    description:
      - Path to the pcsd tokens file.
      - Function calculated default /var/lib/pcsd/tokens (when root) or ~/.pcs/tokens (other users)
    type: str
  username:
    description:
      - User to authenticate with.
    type: str
    default: "hacluster"
    aliases:
      - user
      - u
  password:
    description:
      - Password to authenticate with.
    type: str
    aliases:
      - p
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
- name: Authenticate between nodes
  community.pacemaker.pacemaker_authentication:
    members:
      - amazonlinux1.pacemaker
      - amazonlinux2.pacemaker
      - amazonlinux3.pacemaker
    username: "hacluster"
    password: "MySecretPassword2023!@$"
    state: "present"

- name: Removes the specified host from the pcsd tokens file
  community.pacemaker.pacemaker_authentication:
    members:
      - amazonlinux3.pacemaker
    username: "hacluster"
    password: "MySecretPassword2023!@$"
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

from ansible_collections.community.pacemaker.plugins.module_utils.pacemaker_common import (
    file_exists,
    get_json_file,
    valid_pcsd_tokens_data,
    pcsd_tokens_file,
    build_cluster_auth_cmd
)

import os
import json
import traceback


def main():
    argument_spec = pacemaker_common_argument_spec()
    argument_spec.update(
        members=dict(type='list', elements='str', aliases=["hosts"]),
        state=dict(type='str', choices=["present", "absent"], default="present"),
        pcsd_tokens_file=dict(type='str'),
        username=dict(type='str', default="hacluster", aliases=["user", "u"]),
        password=dict(type='str', aliases=["p"], no_log=True),
        local=dict(type='bool', default=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    rc, out, err = None, None, None
    result = {}
    state = module.params["state"]
    if state == "present" and module.params['members'] is None:
        module.fail_json(msg="members parameter is required when state is present")
    tokens_file = module.params["pcsd_tokens_file"]
    if tokens_file is None:
        tokens_file = pcsd_tokens_file()  # Set to default root or user specific
    try:
        pcsd_file_exists = file_exists(tokens_file)

        if state == "present":
            members_without_port = [i.split(':')[0] for i in module.params['members']]
            port = None
            if len(module.params['members']) > 0 and ':' in module.params['members'][0]:
                port = module.params['members'][0].split(':')[1]
            if pcsd_file_exists:
                if module.params["force"]:  # auth everything regardless of current state
                    cmd = build_cluster_auth_cmd(module, members_without_port, port)
                    if module.check_mode is False:
                        (rc, out, err) = module.run_command(cmd)
                    if rc == 0 or module.check_mode is True:
                        result["changed"] = True
                        result["msg"] = "All provided members were authenticated"
                    else:
                        if module.params["debug"] is True:
                            result["err"] = err
                            result["out"] = out
                        module.fail_json(msg="An error was encountered rc {0}".format(rc), **result)
                else:
                    tokens_data = get_json_file(tokens_file)
                    if valid_pcsd_tokens_data(tokens_data):
                        if sorted(members_without_port) == sorted(tokens_data["tokens"].keys()):
                            result["changed"] = False
                            result["msg"] = "All members have tokens in {0}".format(tokens_file)
                        else:
                            members_to_add = list(set(members_without_port) - set(tokens_data["tokens"].keys()))
                            members_to_remove = list(set(tokens_data["tokens"].keys()) - set(members_without_port))
                            cmd = build_cluster_auth_cmd(module, members_to_add, port)
                            if len(members_to_add) > 0:
                                if module.check_mode is False:
                                    (rc, out, err) = module.run_command(cmd)
                                if rc == 0 or module.check_mode is True:
                                    result["changed"] = True
                                    result["msg"] = "The following members were authenticated {0}".format(' '.join(sorted(members_to_add)))
                            # Next bit to remove keys from members and ports dicts, this could be non-atomic, rethink later
                            json_data = get_json_file(tokens_file)  # get new data
                            if len(members_to_remove) > 0:
                                if module.check_mode is False:
                                    for m in members_to_remove:
                                        json_data["tokens"].pop(m)
                                        json_data["ports"].pop(m)
                                    with open(tokens_file, 'w') as f:
                                        f.write(json.dumps(json_data))
                                result["changed"] = True
                                prepend_msg = ""
                                if 'msg' in result:
                                    prepend_msg = ", "
                                result["msg"] = "{0}{1}The following members were removed {2}".format(result.get('msg', ''), 
                                                                                                      prepend_msg, 
                                                                                                      ' '.join(sorted(members_to_remove)))
                    else:
                        module.fail_json(msg="The pcsd token file is not valid {0}".format(tokens_file))
            else:
                cmd = build_cluster_auth_cmd(module, members_without_port, port)
                if module.check_mode is False:
                    (rc, out, err) = module.run_command(cmd)
                if rc == 0 or module.check_mode is True:
                    result["changed"] = True
                    result["msg"] = "All provided members were authenticated"
                else:
                    if module.params["debug"] is True:
                        result["err"] = err
                        result["out"] = out
                    module.fail_json(msg="An error was encountered rc {0}".format(rc), **result)
        elif state == "absent":
            if pcsd_file_exists:
                if module.check_mode is False:
                    os.remove(tokens_file)
                result["changed"] = True
                result["msg"] = "The pcsd tokens file has been removed {0}".format(tokens_file)
            else:
                result["changed"] = False
                result["msg"] = "The pcsd tokens file has not been configured {0}".format(tokens_file)
    except Exception as excep:
        if module.params["debug"]:
            excep = traceback.format_exc()
        module.fail_json(msg='Error: %s' % to_native(excep))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
