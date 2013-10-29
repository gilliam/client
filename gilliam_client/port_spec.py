# Copyright 2013 Johan Rydberg.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple


PortSpec = namedtuple('PortSpec', ['public', 'private'])


def parse_port_spec(spec):
    if not ':' in spec:
        return PortSpec(public=None, private=int(spec))

    public, private = spec.split(':')
    if not public:
        public = private
    return PortSpec(public=int(public), private=int(private))


def fmt_port_spec(port_spec):
    if port_spec.public:
        return '%d:%d' % (port_spec.public, port_spec.private)
    else:
        return str(port_spec.private)


def merge_port_specs(left, right):
    port_specs = {ps.private: ps for ps in (
            parse_port_spec(str(ps)) for ps in left)}
    for spec in right:
        port_spec = parse_port_spec(spec)
        port_specs[port_spec.private] = port_spec
    return [fmt_port_spec(ps) for ps in port_specs.values()]
