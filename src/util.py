from datetime import datetime, timezone, timedelta
import re
from typing import *

filename_re = re.compile(r"/[^/]+$")
name_re = re.compile(r"^.*/(([^/]+)-\d{4,}-\d\d-\d\dT\d{4}\.apt\..+\.(.+))$")
source_re = re.compile(r"^/dev/")


def extract_directory(path: str) -> str:
    """
    >>> extract_directory('/mnt/backups/work-2017-05-03T1020.apt.dd.gz')
    '/mnt/backups'
    """
    return re.sub(filename_re, '', path)


def extract_filename(path: str) -> str:
    """
    >>> extract_filename('/mnt/backups/work-2017-05-03T1020.apt.dd.gz')
    'work-2017-05-03T1020.apt.dd.gz'
    """
    m = re.fullmatch(name_re, path)
    return m.group(1)


def extract_name(path: str) -> str:
    """
    >>> extract_name('/mnt/backups/work-2017-05-03T1020.apt.dd.gz')
    'work'
    """
    m = re.fullmatch(name_re, path)
    return m.group(2)


def extract_compression_option(path: str) -> str:
    """
    >>> extract_compression_option('/mnt/backups/work-2017-05-03T1020.apt.dd.gz')
    'gz'

    >>> extract_compression_option('/mnt/123/main-2017-05-03T1020.apt.dd.zstd')
    'zst'
    """
    m = re.fullmatch(name_re, path)
    z_option = m.group(3)
    if z_option == 'zstd':  # fix v0.14 extension
        z_option = 'zst'
    return z_option


def rm_dev(source: str) -> str:
    """
    >>> rm_dev("/dev/sda1")
    'sda1'
    """
    return re.sub(source_re, '', source)


def round_to_second(delta: timedelta) -> timedelta:
    micros = delta.microseconds
    truncated = delta - timedelta(microseconds=micros)
    if micros >= 500000:  # round half up
        return truncated + timedelta(seconds=1)
    return truncated


def default_datetime_to_utc(message):
    """Recursively add UTC as tz when missing, pyyaml seems to ignore yaml datetime 'Z' endings"""
    def handle(val, setter: Callable):
        if type(val) is datetime:
            setter(val.replace(tzinfo=val.tzinfo or timezone.utc))
        elif isinstance(val, Dict):
            do_in_dict(val)
        elif isinstance(val, List):
            do_in_list(val)

    def do_in_list(values: List):
        for idx, val in enumerate(values):
            def overwrite(v):
                values[idx] = v
            handle(val, overwrite)

    def do_in_dict(values: Dict):
        for key, val in values.items():
            def overwrite(v):
                values[key] = v
            handle(val, overwrite)

    if isinstance(message, Dict):
        do_in_dict(message)
    elif isinstance(message, List):
        do_in_list(message)
    else:
        raise Exception('Unknown type: ' + type(message))
    return message
