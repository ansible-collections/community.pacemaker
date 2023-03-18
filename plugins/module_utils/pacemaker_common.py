from __future__ import absolute_import, division, print_function
__metaclass__ = type
import os
import json
import getpass as gt


def file_exists(file):
    return os.path.exists(file)

def get_json_file(file):
    data = None
    with open(file, 'r') as json_file:
        data = json.load(json_file)
    return data

def valid_pcsd_tokens_data(json_data):
    """
    Validates whether the json read from the pcsd tokens file looks good.

    The file if either /var/lib/pcsd/tokens (when setup with root), or ~/.pcs/tokens

    The expected data structure is something like...

    {
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
    """
    good = False
    if sorted(["format_version", "data_version", "tokens", "ports"]) == \
            sorted(json_data.keys()) and \
            isinstance(json_data["tokens"], dict) and \
            isinstance(json_data["ports"], dict):
        good = True
    return good


def pcsd_tokens_file(user=None):
    """
    @user - manual user override,  mainly for testing
    """
    if user is None:
        user = gt.getuser()
    token_file = "~/.pcs/tokens"
    if user == "root":
        token_file = "/var/lib/pcsd/tokens"
    return token_file

def build_cluster_auth_cmd(module, members_list, port=None):
    """
    Build the command to auth instances for pcsd
    @module - Ansible module object
    @members_list - members to auth to pcsd
    @port - pcsd port, if not default
    """
    if port == None:
        port = ""
    else:
        port = f":{port}"
    members_str = " ".join(f"{item}{port}" for item in members_list)
    cmd_base = f"{module.params['pcs_util']} cluster auth {members_str}"
    cmd_base = f"{cmd_base} -u {module.params['username']} -p {module.params['password']}"
    if module.params["local"]:
        cmd_base = f"{cmd_base} --local"
    if module.params["force"]:
        cmd_base = f"{cmd_base} --force"
    return cmd_base

def build_cluster_setup_cmd(module, members_list):
    """
    Build the command for pcs cluster setup
    @module - Ansible module object
    @members_list - members to add to the cluster
    """

    members_str = " ".join(f"{item}" for item in members_list)
    cmd_base = f"{module.params['pcs_util']} cluster setup"
    if module.params["state"] == "started":
        cmd_base = f"{cmd_base} --start"
    if module.params["enabled"]:
        cmd_base = f"{cmd_base} --enable"
    if module.params["local"]:
        cmd_base = f"{cmd_base} --local"
    if module.params["force"]:
        cmd_base = f"{cmd_base} --force"
    if module.params["wait"] is not None:
        cmd_base = f"{cmd_base} --wait {module.params['wait']}"
    cmd_base = f"{cmd_base} --name {module.params['name']} {members_str}"
    return cmd_base

def get_cluster_name(corosync_file="/etc/corosync/corosync.conf"):
    """
    Return the cluster name from a corosync config file
    @corosync_file - Path to the corosync conf file
    """
    with open(corosync_file) as f:
        for line in f:
            if "cluster_name" in line and line.startswith("#") == False:
                cluster_name = line.split(": ")[1].strip()
                break
    return cluster_name
