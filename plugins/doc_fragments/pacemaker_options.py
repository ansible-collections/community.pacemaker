from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


class ModuleDocFragment(object):
    # Standard documentation
    DOCUMENTATION = r'''
options:
  pcs_util:
    description:
      - The pcs utility.
    type: str
    default: "pcs"
  file:
    description:
      - Perform actions on file instead of active CIB.
    type: str
    default: null
  request_timeout:
    description:
      - Timeout for each outgoing request to another node in seconds.
    type: int
    default: 60
  force:
    description:
      - Run commands with the --force flag.
      - Only use this if you know what you're doing.
    type: bool
    default: false
  debug:
    description:
      - Run commands with the --debug flag and provide the output.
    type: bool
    default: false
'''