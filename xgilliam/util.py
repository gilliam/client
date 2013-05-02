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

from datetime import datetime
import dateutil.parser


def urlchild(base_url, *args):
    return base_url + ''.join([('/%s' % arg) for arg in args])


def from_now(dt):
    """Calculate how many seconds/minutes/hours something happened."""
    if not isinstance(dt, datetime):
        dt = dateutil.parser.parse(dt)
    return datetime.utcnow() - dt


def format_timedelta(td):
    days, s = divmod(td.total_seconds(), 24 * 3600)
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    values = []
    for v, suffix in zip((days, hours, minutes, seconds),
                         ('d', 'h', 'm', 's')):
        if v:
            values.append('%d%s' % (v, suffix))
    return ''.join(values)


def pretty_date(time):
    """
    """
    now = datetime.utcnow()
    diff = now - time 
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff/7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff/30) + " months ago"
    return str(day_diff/365) + " years ago"
