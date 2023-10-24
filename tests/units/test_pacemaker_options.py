from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import unittest
import os
import sys

path = os.path.dirname(os.path.realpath(__file__))
path = "{0}/../../plugins/module_utils".format(path)
sys.path.append(path)
import pacemaker_options


class TestPacemakerArgumentSpecCommonMethods(unittest.TestCase):

    def test_pacemaker_common_argument_spec(self):
        options = pacemaker_options.pacemaker_common_argument_spec()
        self.assertTrue(isinstance(options, dict))
        self.assertTrue(isinstance(options['file'], dict))
