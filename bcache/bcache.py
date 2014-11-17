#!/usr/bin/env python
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see http://www.gnu.org/licenses/.
#
# This plugin was based in https://github.com/pommi/collectd-bcache
# I resolved used

# <Plugin python>
#     ModulePath "/usr/share/collectd-plugins"
#     Encoding "utf-8"
#     LogTraces true
#     Interactive false
#     Import "api"
#     <module api>
#         Verbose true
#     </module>
# </Plugin>

import os
import collectd

SYSFS_BCACHE_PATH = '/sys/fs/bcache/'
METRIC_DELIM = '.'

def log_verbose(msg):
    if not VERBOSE_LOGGING:
        return
    collectd.info('api plugin [verbose]: %s' % msg)

def file_to_lines(fname):
    try:
        with open(fname, "r") as fd:
            return fd.readlines()
    except:
        return []


def file_to_line(fname):
    ret = file_to_lines(fname)
    if ret:
        return ret[0].strip()
    return ''


def interpret_bytes(x):
    '''Interpret a pretty-printed disk size.'''
    factors = {
        'k': 1 << 10,
        'M': 1 << 20,
        'G': 1 << 30,
        'T': 1 << 40,
        'P': 1 << 50,
        'E': 1 << 60,
        'Z': 1 << 70,
        'Y': 1 << 80,
    }

    factor = 1
    if x[-1] in factors:
        factor = factors[x[-1]]
        x = x[:-1]
    return int(float(x) * factor)


def bcache_uuids():
    uuids = []

    if not os.path.isdir(SYSFS_BCACHE_PATH):
        print('# bcache is not loaded.')
        return uuids

    for cache in os.listdir(SYSFS_BCACHE_PATH):
        if not os.path.isdir('%s%s' % (SYSFS_BCACHE_PATH, cache)):
            continue
        uuids.append(cache)

    return uuids


def get_dirty_data(uuid):
    dirty_data = 0
    for obj in os.listdir(os.path.join(SYSFS_BCACHE_PATH, uuid)):
        if obj.startswith('bdev'):
            val = interpret_bytes(file_to_line('%s/%s/%s/dirty_data' %
                                               (SYSFS_BCACHE_PATH, uuid, obj)))
            dirty_data = dirty_data + int(val)
    return dirty_data


def get_cache_ratio(uuid, time):
    for obj in os.listdir(os.path.join(SYSFS_BCACHE_PATH, uuid)):
        if obj.startswith('bdev'):
            hits = float(file_to_line('%s/%s/%s/stats_%s/cache_hits' %
                                    (SYSFS_BCACHE_PATH, uuid, obj, time)))
            misses = float(file_to_line('%s/%s/%s/stats_%s/cache_misses' %
                                      (SYSFS_BCACHE_PATH, uuid, obj, time)))
            if (hits + misses) == 0:
                return 100
            return hits / (hits + misses) * 100
    return 0


def get_cache_result(uuid, stat):
    value = 0
    for obj in os.listdir(os.path.join(SYSFS_BCACHE_PATH, uuid)):
        if obj.startswith('bdev'):
            value = int(file_to_line('%s/%s/%s/stats_five_minute/cache_%s' %
                                    (SYSFS_BCACHE_PATH, uuid, obj, stat)))
    return value


def get_bypassed(uuid):
    value = 0
    for obj in os.listdir(os.path.join(SYSFS_BCACHE_PATH, uuid)):
        if obj.startswith('bdev'):
            value = interpret_bytes(file_to_line('%s/%s/%s/stats_five_minute/bypassed' %
                                               (SYSFS_BCACHE_PATH, uuid, obj)))
    return value


def map_uuid_to_bcache(uuid):
    devices = []
    for obj in os.listdir(os.path.join(SYSFS_BCACHE_PATH, uuid)):
        if obj.startswith('bdev'):
           devices.append(os.path.basename(os.readlink(os.path.join(SYSFS_BCACHE_PATH, uuid, obj, 'dev'))))
    return devices

def configure_callback(conf):
    """Receive configuration block"""
    global VERBOSE_LOGGING
    for node in conf.children:
        if node.key == 'Verbose':
            VERBOSE_LOGGING = bool(node.values[0])
        else:
            collectd.warning('bcache plugin: Unknown config key: %s.' % node.key)

def read_callback():
    uuids = bcache_uuids()

    for uuid in uuids:
        dirty_data = get_dirty_data(uuid)
        devices = map_uuid_to_bcache(uuid)

        for device in devices:
            key_root = METRIC_DELIM.join([device, 'df_complex-dirty_data'])
            val = collectd.Values(plugin='bcache')
            val.type = 'gauge'
            val.type_instance = key_root
            val.values = [int(dirty_data)]
            val.dispatch()
            log_verbose("New root: %s - Values: %s " % (key_root, dirty_data))

            for t in ['five_minute', 'hour', 'day', 'total']:
                cache_ratio = get_cache_ratio(uuid, t)
                key_root = METRIC_DELIM.join([device, 'cache_ratio', t])
                val = collectd.Values(plugin='bcache')
                val.type = 'gauge'
                val.type_instance = key_root
                val.values = [int(cache_ratio)]
                val.dispatch()
                log_verbose("New root: %s - Values: %s " % (key_root,  cache_ratio))

            for c in ['bypass_hits', 'bypass_misses', 'hits', 'miss_collisions', 'misses', 'readaheads']:
                cache_result = get_cache_result(uuid, c)
                key_root = METRIC_DELIM.join([device, 'cache_stats', c])
                val = collectd.Values(plugin='bcache')
                val.type = 'gauge'
                val.type_instance = key_root
                val.values = [int(cache_result)]
                val.dispatch()
                log_verbose("New root: %s - Values: %s " % (key_root,  cache_result))

            bypassed = get_bypassed(uuid)
            key_root = METRIC_DELIM.join([device, 'bypassed'])
            val = collectd.Values(plugin='bcache')
            val.type = 'gauge'
            val.type_instance = key_root
            val.values = [int(bypassed)]
            val.dispatch()
            log_verbose("New root: %s - Values: %s " % (key_root,  bypassed))

collectd.register_config(configure_callback)
collectd.register_read(read_callback)
