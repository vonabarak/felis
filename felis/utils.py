# -*- coding: utf-8 -*-
import string
import subprocess
import shlex
from django_q.tasks import async
from felis.errors import *


# TODO: rewrite to expand_number format
# https://www.freebsd.org/cgi/man.cgi?query=expand_number&sektion=3&apropos=0&manpath=FreeBSD+11.0-RELEASE+and+Ports
def size_prefixed(size_in_bytes):
    """Gets integer of bytes and returns a string of size with metric prefix"""

    if size_in_bytes is None:
        return 'none'

    p = ''  # no prefix is bytes
    # terabyte
    v = size_in_bytes // 1024 ** 4
    if v:
        p = 'T'
    # gigabyte
    v = size_in_bytes // 1024 ** 3
    if v:
        p = 'G'
    # megabyte
    v = size_in_bytes // 1024 ** 2
    if v:
        p = 'M'
    # kilobyte
    v = size_in_bytes // 1024
    if v:
        p = 'K'
    return '{value}{prefix}'.format(value=v, prefix=p)


def render_command(model, command):
    """Replaces curly-braced words in `command' with values of corresponding models fields"""
    if command is None or model is None:
        return
    return command.format(**{
        i[1].split('.')[0]: getattr(model, i[1].split('.')[0])
        for i
        in string.Formatter().parse(command.strip())
        if i is not None and i[1] is not None
        })

def run_shell_command(command, sudo=True, **kwargs):
    if sudo:
        sudo_cmd = ['sudo']
    else:
        sudo_cmd = list()
    with subprocess.Popen(
                    sudo_cmd + shlex.split(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs
    ) as p:
        stdout, stderr = p.communicate()
        return p.returncode, stdout, stderr



# def sort_by_priority(itemset, limit):
#     """
#     Function to sort an iterable of objects which have `priority' attribute.
#     Drops items with priority <= limit
#     """
#     itemdict = dict()
#     for i in itemset:
#         if i.priority <= limit:
#             continue
#         if not i.priority in itemdict:
#             itemdict[i.priority] = set()
#         itemdict[i.priority].add(i)
#     sorteditemlist = list()
#     for i in reversed(sorted(itemdict.keys())):
#         for j in itemdict[i]:
#             sorteditemlist.append(j)
#     return sorteditemlist
