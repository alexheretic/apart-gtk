from datetime import timedelta
import re

filename_re = re.compile(r"/[^/]+$")
name_re = re.compile(r"^.*/(([^/]+)-\d{4,}-\d\d-\d\dT\d{4}\.apt\..+\..+)$")
source_re = re.compile(r"^/dev/")


def extract_directory(path: str) -> str:
    return re.sub(filename_re, '', path)


def extract_filename(path: str) -> str:
    m = re.fullmatch(name_re, path)
    return m.group(1)


def extract_name(path: str) -> str:
    m = re.fullmatch(name_re, path)
    return m.group(2)


def rm_dev(source: str) -> str:
    return re.sub(source_re, '', source)


def round_to_second(delta: timedelta) -> timedelta:
    micros = delta.microseconds
    truncated = delta - timedelta(microseconds=micros)
    if micros >= 500000:  # round half up
        return truncated + timedelta(seconds=1)
    return truncated
