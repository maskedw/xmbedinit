#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from __future__ import division
from __future__ import print_function
from __future__ import with_statement

from pkg_resources import resource_filename
import os
import sys
import re
from pathlib import Path
import argparse
import errno
import shutil
import subprocess
import jinja2


verbose = False


def vlog(*args, **kwargs):
    if verbose:
        print(*args, **kwargs)


def set_verbose(value):
    global verbose
    verbose = value


def get_template(name):
    root = resource_filename(__name__, 'templates')
    template = jinja2.Environment(
        loader=jinja2.FileSystemLoader(root)
    ).get_template(name)

    return template


def save(text, path):
    path = Path(path)
    if path.suffix == '.bat':
        text = text.replace('\n', '\r\n')
    with path.open('w', encoding='utf8') as f:
        f.write(text)

    if path.suffix == '.sh' and os.name != 'nt':
        subprocess.check_call('chmod +x "{}" '.format(path), shell=True)


def render(args, dest_dir, templates):
    for t in templates:
        t = str(t)
        ret = get_template(t).render(args)
        save(ret, dest_dir.joinpath(t))


def mkdir_p(path):
    path = str(path)
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def export_files(dest, flielist):
    dest = Path(dest)
    for f in flielist:
        d = dest.joinpath(f)
        vlog('copy => {}'.format(d))
        mkdir_p(d.parent)
        shutil.copyfile(str(f), str(d))


class Parser():
    def __init__(self):
        self.lines = None

    def parse_makefile(self, makefile):
        with open(makefile) as f:
            lines = f.read().splitlines()
        objects = self.get_paths(lines, 'OBJECTS')
        self.sources = self.find_matching_suffix(objects, ['.c', '.cpp', '.S'])
        self.include_dirs = self.get_paths(lines, 'INCLUDE_PATHS')
        self.headers = self.find_headers(self.include_dirs)
        self.definitions = self.get_definitions(lines, 'CXX_FLAGS')
        self.arch_opts = self.get_arch_opts(lines)
        self.linker_flags = self.get_linker_flags(lines)
        self.link_libraries = self.get_link_libraries(lines)
        self.extra_opts = self.get_extra_opts(lines)
        self.warning_opts = self.get_warning_opts(lines)

    def parse_mbed_config(self, mbed_config):
        with open(mbed_config) as f:
            lines = f.read().splitlines()
            regex = re.compile(
                '^#define\s+(?P<name>[^\s]+)\s+(?:(?P<value>.*))//(?P<comment>.*)') # noqa
            config_definitions = []
            for l in lines:
                m = regex.match(l)
                if m:
                    name = m.group('name')
                    value = m.group('value').strip()
                    comment = m.group('comment')
                    x = '-D' + name
                    if value:
                        x += '=' + value
                    # Padding for alignment
                    if len(x) < 55:
                        x += ' ' * (55 - len(x))
                    x += ' #' + comment
                    config_definitions.append(x)
            self.config_definitions = config_definitions

    def find_headers(self, include_dirs):
        result = []
        globs = ['*.h', '*.hpp']
        for d in include_dirs:
            for g in globs:
                for header in Path(d).glob(g):
                    result.append(header)
        return result

    def find_matching_suffix(self, filelist, suffixes):
        result = []
        for f in filelist:
            for s in suffixes:
                x = Path(f).with_suffix(s)
                if x.exists():
                    result.append(x)
        return result

    def get_definitions(self, lines, var_name):
        values = self.get_values(lines, var_name)
        regex = re.compile(r'^(-D.*)')
        result = []
        for v in values:
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def get_values(self, lines, var_name):
        regex = re.compile('^' + var_name + r'\s*[+:]*\=\s*(.*)')
        result = []
        for line in lines:
            m = regex.match(line)
            if m:
                result.append(m.group(1))
        return result

    def get_paths(self, lines, var_name):
        tmp = self.get_values(lines, var_name)
        result = []
        for x in tmp:
            pos = x.find('mbed-os')
            if pos >= 0:
                x = x[pos:]
                ignores = ['frameworks', 'TESTS_COMMON']
                skip = False
                for ignore in ignores:
                    if x.find(ignore) != -1:
                        skip = True
                        break
                if skip:
                    continue
                result.append(x)
        return result

    def get_link_libraries(self, lines):
        result = []
        values = self.get_values(lines, 'LD_SYS_LIBS')[0].split(' ')
        regex = re.compile('^-l(.*)')
        for v in values:
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def get_linker_flags(self, lines):
        result = []
        values = self.get_values(lines, 'LD_FLAGS')[0]
        values = values.split(' ')
        regex = re.compile('^(-Wl,.*)')
        for v in values:
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def strip_quote(self, str_):
        is_quote_single = str_.startswith("'") and str_.endswith("'")
        is_quote_double = str_.startswith('"') and str_.endswith('"')
        if is_quote_single or is_quote_double:
            str_ = str_[1:-1]
        return str_

    def get_warning_opts(self, lines):
        result = []
        values = self.get_values(lines, 'CC')[0]
        values = values.split(' ')
        for v in values:
            v = self.strip_quote(v)
            regex = re.compile('^(-W.*)')
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def get_extra_opts(self, lines):
        result = []
        values = self.get_values(lines, 'CC')[0]
        values = values.split(' ')
        for v in values:
            v = self.strip_quote(v)
            regex = re.compile('^(-f.*)')
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def get_arch_opts(self, lines):
        result = []
        values = self.get_values(lines, 'CC')[0]
        values = values.split(' ')
        for v in values:
            v = self.strip_quote(v)
            arch_opts = [
                r'^(-mthumb)',
                r'^(-mcpu\=.*)',
                r'^(-mfpu\=.*)',
                r'^(-mfloat-abi\=.*)'
            ]
            for opt in arch_opts:
                regex = re.compile(opt)
                m = regex.match(v)
                if m:
                    result.append(m.group(1))
                    break
        return result


def main():
    argparser = argparse.ArgumentParser(
        description='This tool will help local development of mbed'
    )
    argparser.add_argument(
        '-m', '--target',
        required=True,
        help='Compile target MCU. @see https://github.com/ARMmbed/mbed-cli')
    argparser.add_argument(
        '-T', '--tag',
        required=True,
        help='Tag of mbed @see https://github.com/ARMmbed/mbed-os/releases')
    argparser.add_argument(
        '-d', '--dest',
        required=False,
        default='.',
        help='Directory of export destination')
    argparser.add_argument(
        '-v', '--verbose',
        required=False,
        default=False,
        action='store_true',
        help='Verbose output')
    args = argparser.parse_args()
    set_verbose(args.verbose)

    dest = Path(args.dest).resolve()
    if not dest.exists():
        sys.exit('"{}" is not exists'.format(dest))
    if not dest.is_dir():
        sys.exit('"{}" is not directory'.format(dest))

    work_dir = Path(os.path.expanduser('~/.cache/xmbedinit'))
    mkdir_p(work_dir)

    mbed_tag = args.tag
    mbed_dir = work_dir.joinpath(mbed_tag)
    mbed_target = args.target
    mkdir_p(mbed_dir)

    os.chdir(str(mbed_dir))

    if not Path('mbed-os').exists():
        url = 'https://github.com/ARMmbed/mbed-os.git'
        cmd = 'git clone --depth=1 -b {} {}'.format(mbed_tag, url)
        subprocess.check_call(cmd, shell=True)

    with Path('main.cpp').open('w') as f:
        f.write(u'int main(void) { return 0; }')

    cmd = 'mbed compile -t GCC_ARM -m {}'.format(mbed_target)
    subprocess.check_call(cmd, shell=True)

    cmd = 'mbed export -i GCC_ARM -m {}'.format(mbed_target)
    subprocess.check_call(cmd, shell=True)

    vlog('Parse Files ...')
    parser = Parser()
    parser.parse_makefile('Makefile')
    parser.parse_mbed_config('mbed_config.h')

    vlog('Copy files ...')
    export_files(dest, parser.headers)
    export_files(dest, parser.sources)
    shutil.copyfile(
        'BUILD/{}/GCC_ARM/.link_script.ld'.format(mbed_target),
        str(dest.joinpath('linker_script.ld')))

    # ----------------------------------------
    cmake_dir = dest.joinpath('CMake')
    mkdir_p(str(cmake_dir))
    args = {}

    args['project_name'] = dest.stem
    args['url'] = 'https://github.com/ARMmbed/mbed-os.git'
    args['tag'] = mbed_tag
    args['target'] = mbed_target
    args['warning_opts'] = parser.warning_opts
    args['arch_opts'] = parser.arch_opts
    args['extra_opts'] = parser.extra_opts
    args['include_dirs'] = [Path(x).as_posix() for x in parser.include_dirs]
    args['definitions'] = parser.definitions
    args['link_libraries'] = parser.link_libraries
    args['linker_flags'] = parser.linker_flags
    args['sources'] = [Path(x).as_posix() for x in parser.sources]
    args['headers'] = [Path(x).as_posix() for x in parser.headers]
    args['config_definitions'] = parser.config_definitions

    templates = [
        'mbed.cmake',
        'toolchain-arm-none-eabi-gcc.cmake',
    ]
    render(args, cmake_dir, templates)

    templates = [
        'build.sh',
        'build-debug.bat',
        'build-release.bat',
        'build-debug.sh',
        'build-release.sh',
        'build-compile_commands.sh',
        'xdbinit.log',
        'CMakeLists-template.txt',
    ]
    render(args, dest, templates)


if __name__ == "__main__":
    main()
