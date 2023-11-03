from __future__ import absolute_import, division, print_function
__metaclass__ = type


def pacemaker_common_argument_spec():
    options = dict(
        pcs_util=dict(type='str', default="pcs"),
        file=dict(type='str', default=None),
        request_timeout=dict(type='int', default=60),
        force=dict(type='bool', default=False),
        debug=dict(type='bool', default=False),
    )
    return options
