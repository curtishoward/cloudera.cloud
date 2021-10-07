#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2021 Cloudera, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.cdp_common import CdpModule


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: de 
short_description: Enable and Disable CDP Data Engineering Services 
description:
    - Enable or Disable CDP Data Engineering Service
author:
  - "Curtis Howard (@curtis)"
requirements:
  - cdpy
options:
  name:
    description:
      - The name of the CDE Service 
    type: str
    required: True
    aliases:
      - name
  environment:
    description:
      - CDP environment where CDE service should be enabled 
    type: str
    required: True
    aliases:
      - env
  instance_type:
    description:
      - Instance type of the cluster for CDE Service
    type: str
    required: True
    sample:
      - (AWS) m5.2xlarge    
  minimum_instances:
    description:
    - Minimum Instances for the CDE Service
    type: int
    required: True
  maximum_instances:
    description:
    - Maximum Instances for the CDE Service
    type: int
    required: True
  minimum_spot_instances:
    description:
    - Minimum Spot Instances for the CDE Service
    type: int
    required: False 
  maximum_spot_instances:
    description:
    - Maximum Spot Instances for the CDE Service
    type: int
    required: False
  chart_value_overrides:
    description:
    - Chart overrides for enabling a service 
    type: list 
    required: False
    contains:
      chart_name:
        description:
          - The key/value pair for the chart_name/override 
        type: str
        required: False
  enable_public_endpoint:
    description:
    - Creates a CDE endpoint (Load Balancer) in a publicly accessible subnet
    type: bool
    required: False
  enable_workload_analytics:
    description:
    - If set false, diagnostic information about job and query execution is sent to Cloudera Workload Manager 
    type: bool
    required: False
  initial_instances:
    description:
    - Initial Instances when the service is enabled
    type: int
    required: False 
  initial_spot_instances:
    description:
    - Initial spot Instances when the service is enabled
    type: int
    required: False 
  root_volume_size:
    description:
    - EBS volume size in GB
    type: int 
    required: False
  skip_validation:
    description:
    - Skip Validation check.
    type: bool
    required: False
  tags:
    description:
    - User defined labels that tag all provisioned cloud resources
    type: dict
    required: False
    contains:
      key:
        description:
          - The key/value pair for the tag
        type: str
        required: False
  use_ssd:
    description:
    - Instance local storage (SSD) would be used for the workload filesystem (Example - spark local directory). Currently supported only for aws services
    type: bool
    required: False
  whitelist_ips:
    description:
    - List of CIDRs that would be allowed to access kubernetes master API server
    type: array
    elements: str
    required: False
  force:
    description:
      - Flag to force delete a service even if errors occur during deletion.
    type: bool
    required: False
    default: False
    aliases:
      - force_delete
  state:
    description:
      - The declarative state of the CDE service
    type: str
    required: False
    default: present
    choices:
      - present
      - absent
  wait:
    description:
      - Flag to enable internal polling to wait for the DE Service to achieve the declared state.
      - If set to FALSE, the module will return immediately.
    type: bool
    required: False
    default: True
  delay:
    description:
      - The internal polling interval (in seconds) while the module waits for the DE Service to achieve the declared
        state.
    type: int
    required: False
    default: 60
    aliases:
      - polling_delay
  timeout:
    description:
      - The internal polling timeout (in seconds) while the module waits for the DE Service to achieve the declared
        state.
    type: int
    required: False
    default: 7200
    aliases:
      - polling_timeout
'''

# TODO: dcoument 'EXAMPLES' for DE 
# TODO: document 'RETURN' for DE 

class DEService(CdpModule):
    def __init__(self, module):
        super(DEService, self).__init__(module)

        # Set variables
        self.name = self._get_param('name')
        self.env = self._get_param('environment')

        self.instance_type = self._get_param('instance_type')

        self.minimum_instances = self._get_param('minimum_instances')
        self.maximum_instances = self._get_param('maximum_instances')
        self.minimum_spot_instances = self._get_param('minimum_spot_instances')
        self.maximum_spot_instances = self._get_param('maximum_spot_instances')
        self.chart_value_overrides = self._get_param('chart_value_overrides')
        self.enable_public_endpoint = self._get_param('enable_public_endpoint')
        self.enable_workload_analytics = self._get_param('enable_workload_analytics')
        self.initial_instances = self._get_param('initial_instances')
        self.initial_spot_instances = self._get_param('initial_spot_instances')
        self.root_volume_size = self._get_param('root_volume_size')
        self.skip_validation = self._get_param('skip_validation')
        self.tags = self._get_param('tags')
        self.use_ssd = self._get_param('use_ssd')
        self.whitelist_ips = self._get_param('whitelist_ips')

        self.state = self._get_param('state')
        self.force = self._get_param('force')
        self.wait = self._get_param('wait')
        self.delay = self._get_param('delay')
        self.timeout = self._get_param('timeout')

        # Initialize return values
        self.service = None 

        # Initialize cluster (service) ID
        self.cluster_id = None

        # Execute logic process
        self.process()

    @CdpModule._Decorators.process_debug
    def process(self):
        for service in self.cdpy.de.list_services(env=self.env, remove_deleted=True):
            if service['name'] == self.name:
                self.cluster_id = service['clusterId']
                break
        initial_desc = self.cdpy.de.describe_service(self.cluster_id) if self.cluster_id else None

        # If a service under the name/env pair was found (excluding disabled services)
        if initial_desc and initial_desc['status']:
            # Disable the Service if expected state is 'absent' 
            if self.state == 'absent':
                if self.module.check_mode:
                    self.service = initial_desc
                else:
                    # Service is available - disable it
                    if initial_desc['status'] in self.cdpy.sdk.REMOVABLE_STATES:
                        self.service = self._disable_service()
                    # Service exists but is not in a disable-able state (could be in the process of
                    # provisioning, disabling, or may be in a failed state)
                    else:
                        self.module.warn("DE Service is not in a removable state: %s" % 
                                         initial_desc['status'])
                        if self.wait:
                            self.module.warn(
                                "Waiting for DE Service to reach Active or Disabled state")
                            current_desc = self._wait_for_state(self.cdpy.sdk.REMOVABLE_STATES +
                                                                self.cdpy.sdk.STOPPED_STATES)
                            # If we just waited fo the service to be provisioned, then dis-abled it
                            if current_desc['status'] in self.cdpy.sdk.REMOVABLE_STATES:
                                self.service = self._disable_service()
                            else:
                                self.service = current_desc
                                if current_desc['status'] not in self.cdpy.sdk.STOPPED_STATES:
                                    self.module.warn("DE service did not disable successfully")
            elif self.state == 'present':
                # Check the existing configuration and state
                self.module.warn("DE Service already present and configuration validation" +
                                 "and reconciliation is not supported")
                if self.wait:
                    current_desc = self._wait_for_state(self.cdpy.sdk.REMOVABLE_STATES +
                                                        self.cdpy.sdk.STOPPED_STATES)
                    # If we just waited for the service to be disabled, then enable it
                    if current_desc['status'] in self.cdpy.sdk.STOPPED_STATES:
                        self.service = self._enable_service()
            else:
                self.module.fail_json(
                    msg="State %s is not valid for this module" % self.state)

        # Else if the Service does not exist
        else:
            if self.state == 'absent':
                self.module.log(
                    "DE service %s already absent or terminated in Environment %s" %
                    (self.name, self.env))
            # Create the Service
            elif self.state == 'present':
                if not self.module.check_mode:
                    self.service = self._enable_service()
            else:
                self.module.fail_json(
                    msg="State %s is not valid for this module" % self.state)

    def _enable_service(self):
        result = self.cdpy.de.enable_service(
            name=self.name,
            env=self.env,
            instance_type=self.instance_type,
            minimum_instances=self.minimum_instances,
            maximum_instances=self.maximum_instances,
            minimum_spot_instances=self.minimum_spot_instances,
            maximum_spot_instances=self.maximum_spot_instances,
            chart_value_overrides=self.chart_value_overrides,
            enable_public_endpoint=self.enable_public_endpoint,
            enable_workload_analytics=self.enable_workload_analytics,
            initial_instances=self.initial_instances,
            initial_spot_instances=self.initial_spot_instances,
            root_volume_size=self.root_volume_size,
            skip_validation=self.skip_validation,
            tags=self.tags,
            use_ssd=self.use_ssd,
            whitelist_ips=self.whitelist_ips
        ) 
        self.cluster_id = result['clusterId']
        if self.wait:
            current_desc = self._wait_for_state(self.cdpy.sdk.REMOVABLE_STATES)
            if current_desc['status'] not in self.cdpy.sdk.REMOVABLE_STATES:
                self.module.warn("DE service did not enable successfully")
            return current_desc
        else:
            return None

    def _disable_service(self):
        self.cdpy.de.disable_service(self.cluster_id)
        if self.wait:
            current_desc = self._wait_for_state(self.cdpy.sdk.STOPPED_STATES)
            if current_desc['status'] not in self.cdpy.sdk.STOPPED_STATES:
                self.module.warn("DE service did not disable successfully")
            return current_desc
        else:
            return None

    def _wait_for_state(self, state):
        return self.cdpy.sdk.wait_for_state(
            describe_func=self.cdpy.de.describe_service,
            params=dict(cluster_id=self.cluster_id),
            field='status', state=state, delay=self.delay,
            timeout=self.timeout
        )

    @staticmethod
    def c_log(msg):
        import datetime
        f = open("/runner/project/c_log.txt", "a")
        f.write(str(datetime.datetime.now()) + '\t' + msg + '\n')
        f.close()


def main():
    module = AnsibleModule(
        argument_spec=CdpModule.argument_spec(
            name=dict(required=True, type='str'),
            environment=dict(required=True, type='str', aliases=['env']),
            instance_type=dict(required=True, type='str'),
            minimum_instances=dict(required=True, type='int'),
            maximum_instances=dict(required=True, type='int'),
            minimum_spot_instances=dict(required=False, type='int', default=0),
            maximum_spot_instances=dict(required=False, type='int', default=0),
            chart_value_overrides=dict(required=False, type='list', default=None), 
            enable_public_endpoint=dict(required=False, type='bool', default=False),
            enable_workload_analytics=dict(required=False, type='bool', default=False),
            initial_instances=dict(required=False, type='int', default=None),
            initial_spot_instances=dict(required=False, type='int', default=None),
            root_volume_size=dict(required=False, type='int', default=None),
            skip_validation=dict(required=False, type='bool', default=False),
            tags=dict(required=False, type='dict', default=None),
            use_ssd=dict(required=False, type='bool', default=False),
            whitelist_ips=dict(required=False, type='list', elements='str', default=None),
            force=dict(required=False, type='bool', default=False, aliases=['force_delete']),
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            wait=dict(required=False, type='bool', default=True),
            delay=dict(required=False, type='int', aliases=['polling_delay'], default=60),
            timeout=dict(required=False, type='int', aliases=['polling_timeout'], default=7200)
        ),
        supports_check_mode=True
    )

    result = DEService(module)
    output = dict(changed=False, service=(result.service if result.service else {}))

    if result.debug:
        output.update(sdk_out=result.log_out, sdk_out_lines=result.log_lines)

    module.exit_json(**output)


if __name__ == '__main__':
    main()
