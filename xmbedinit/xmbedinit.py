#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from __future__ import division
from __future__ import print_function
from __future__ import with_statement

import pkg_resources
from pkg_resources import resource_filename

import os
import sys
import re
from pathlib import Path, PurePosixPath
import argparse
import errno
import shutil
import subprocess
import jinja2
import json
import pyaml


verbose = False


def vlog(*args, **kwargs):
    if verbose:
        print(*args, **kwargs)


def set_verbose(value):
    global verbose
    verbose = value


def get_template(name):
    root = resource_filename(__name__, 'templates')
    try:
        template = jinja2.Environment(
            loader=jinja2.FileSystemLoader(root)
        ).get_template(name)
    except:
        print(name)
        raise

    return template


def save(text, path):
    path = Path(path)
    if path.suffix == '.bat':
        text = text.replace('\n', '\r\n')
    with path.open('wb') as f:
        f.write(text.encode('utf8'))

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


def make_all_library_info(base_dir):
    result = []
    for x in Path(base_dir).rglob('mbed_lib.json'):
        test_dir = str(Path(base_dir, 'tools', 'test'))
        if os.path.commonprefix([str(x), test_dir]) == test_dir:
            vlog('without test-library:{}'.format(x))
            continue
        vlog('found library: {}'.format(x))

        with x.open() as f:
            try:
                info = json.load(f)
            except json.decoder.JSONDecodeError:
                continue
            info['dir'] = x.parent
            result.append(info)
    return result


class UnusedLibraryFilter():
    def filterd(self, build_info, unused_libraries):
        filterd_build_info = BuildInfo()
        filterd_build_info.definitions = build_info.definitions
        filterd_build_info.arch_opts = build_info.arch_opts
        filterd_build_info.linker_flags = build_info.linker_flags
        filterd_build_info.link_libraries = build_info.link_libraries
        filterd_build_info.c_extra_opts = build_info.c_extra_opts
        filterd_build_info.cxx_extra_opts = build_info.cxx_extra_opts
        filterd_build_info.warning_opts = build_info.warning_opts

        ##############################
        # filter config_definitions
        regex = re.compile(r'library:([-_a-zA-Z0-9]+)')
        unused_library_names = [x['name'] for x in unused_libraries]
        for x in build_info.config_definitions:
            m = regex.search(x)
            if not m:
                filterd_build_info.config_definitions.append(x)
                continue

            x_library_name = m.group(1)
            if x_library_name in unused_library_names:
                filterd_build_info.removed_config_definitions.append(
                    {'removed_by': x_library_name, 'value': x})
            else:
                filterd_build_info.config_definitions.append(x)

        ##############################
        # filter include_dirs
        result = []
        for x in build_info.include_dirs:
            for unused_info in unused_libraries:
                unused_dir = str(unused_info['dir'])
                if os.path.commonprefix([str(x), unused_dir]) == unused_dir:
                    filterd_build_info.removed_include_dirs.append(
                        {'removed_by': unused_info['name'], 'value': x})
                    break
            else:
                filterd_build_info.include_dirs.append(x)

        ##############################
        # filter sources
        for x in build_info.sources:
            x_parent = str(x.parent)
            for unused_info in unused_libraries:
                unused_dir = str(unused_info['dir'])
                if os.path.commonprefix([x_parent, unused_dir]) == unused_dir:
                    filterd_build_info.removed_sources.append(
                        {'removed_by': unused_info['name'], 'value': x})
                    break
            else:
                filterd_build_info.sources.append(x)

        ##############################
        # filter headers
        for x in build_info.headers:
            x_parent = str(x.parent)
            for unused_info in unused_libraries:
                unused_dir = str(unused_info['dir'])
                if os.path.commonprefix([x_parent, unused_dir]) == unused_dir:
                    filterd_build_info.removed_headers.append(
                        {'removed_by': unused_info['name'], 'value': x})
                    break
            else:
                filterd_build_info.headers.append(x)


        return filterd_build_info


class BuildInfo():
    def __init__(self):
        self.sources = []
        self.include_dirs = []
        self.headers = []
        self.definitions = []
        self.arch_opts = []
        self.linker_flags = []
        self.link_libraries = []
        self.c_extra_opts = []
        self.cxx_extra_opts = []
        self.warning_opts = []
        self.config_definitions = []

        self.removed_sources = []
        self.removed_headers = []
        self.removed_config_definitions = []
        self.removed_include_dirs = []


class Parser():
    def parse_makefile(self, makefile, build_info):
        if build_info is None:
            build_info = BuildInfo()

        with open(makefile) as f:
            lines = f.read().splitlines()

        objects                   = self._get_paths(lines, 'OBJECTS')
        build_info.sources        = self._find_matching_suffix(objects, ['.c', '.cpp', '.S'])
        build_info.include_dirs   = self._get_paths(lines, 'INCLUDE_PATHS')
        build_info.headers        = self._find_headers(build_info.include_dirs)
        build_info.definitions    = self._get_definitions(lines, 'CXX_FLAGS')
        build_info.arch_opts      = self._get_arch_opts(lines)
        build_info.linker_flags   = self._get_linker_flags(lines)
        build_info.link_libraries = self._get_link_libraries(lines)
        build_info.cxx_extra_opts = self._get_cxx_extra_opts(lines)
        build_info.c_extra_opts   = self._get_c_extra_opts(lines)
        build_info.warning_opts   = self._get_warning_opts(lines)

        return build_info

    def parse_mbed_config(self, mbed_config, build_info):
        if build_info is None:
            build_info = BuildInfo()

        with open(mbed_config) as f:
            lines = f.read().splitlines()
            regex = re.compile(
                '^#define\s+(?P<name>[^\s]+)\s+(?:(?P<value>.*))//(?P<comment>.*)') # noqa
            config_definitions = []
            for l in lines:
                m = regex.match(l)
                is_braces = False
                if m:
                    name = m.group('name')
                    value = m.group('value').strip()
                    comment = m.group('comment')
                    x = '-D' + name
                    if value:
                        x += '=' + value
                        if value.startswith('{'):
                            is_braces = True

                    if is_braces:
                        x = '"{}"'.format(x)
                    # Padding for alignment
                    if len(x) < 55:
                        x += ' ' * (55 - len(x))
                    x += ' #' + comment
                    config_definitions.append(x)
            build_info.config_definitions = sorted(config_definitions)

        return build_info

    def _find_headers(self, include_dirs):
        result = []
        globs = ['*.h', '*.hpp']
        for d in include_dirs:
            for g in globs:
                for header in Path(d).glob(g):
                    result.append(header)
        result = [Path(x) for x in result]
        return result

    def _find_matching_suffix(self, filelist, suffixes):
        result = []
        for f in filelist:
            for s in suffixes:
                x = Path(f).with_suffix(s)
                if x.exists():
                    result.append(x)
        return result

    def _get_definitions(self, lines, var_name):
        values = self._get_values(lines, var_name)
        regex = re.compile(r'^(-D.*)')
        result = []
        for v in values:
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        result = sorted(result)
        return result

    def _get_values(self, lines, var_name):
        regex = re.compile('^' + var_name + r'\s*[+:]*\=\s*(.*)')
        result = []
        for line in lines:
            m = regex.match(line)
            if not m:
                continue
            value = m.group(1)
            if value in result:
                continue
            result.append(value)
        return result

    def _get_paths(self, lines, var_name):
        tmp = self._get_values(lines, var_name)
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
        result = [Path(x) for x in result]
        return result

    def _get_link_libraries(self, lines):
        result = []
        values = self._get_values(lines, 'LD_SYS_LIBS')[0].split(' ')
        regex = re.compile('^-l(.*)')
        for v in values:
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def _get_linker_flags(self, lines):
        result = []
        values = self._get_values(lines, 'LD_FLAGS')[0]
        values = values.split(' ')
        regex = re.compile('^(-Wl,.*)')
        for v in values:
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def _strip_quote(self, str_):
        is_quote_single = str_.startswith("'") and str_.endswith("'")
        is_quote_double = str_.startswith('"') and str_.endswith('"')
        if is_quote_single or is_quote_double:
            str_ = str_[1:-1]
        return str_

    def _get_warning_opts(self, lines):
        result = []
        values = self._get_values(lines, 'CXX_FLAGS')
        for v in values:
            v = self._strip_quote(v)
            regex = re.compile('^(-W.*)')
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def _get_cxx_extra_opts(self, lines):
        result = []
        values = self._get_values(lines, 'CXX_FLAGS')
        for v in values:
            v = self._strip_quote(v)
            regex = re.compile('^(-f.*)')
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def _get_c_extra_opts(self, lines):
        result = []
        values = self._get_values(lines, 'C_FLAGS')
        for v in values:
            v = self._strip_quote(v)
            regex = re.compile('^(-f.*)')
            m = regex.match(v)
            if m:
                result.append(m.group(1))
        return result

    def _get_arch_opts(self, lines):
        result = []
        values = self._get_values(lines, 'CXX_FLAGS')
        for v in values:
            v = self._strip_quote(v)
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
        description='This tool will help local development of mbed',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
    argparser.add_argument(
        '--version',
        action='version',
        version='%(prog)s {}'.format(
            pkg_resources.require('xmbedinit')[0].version))
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
    build_info = parser.parse_makefile('Makefile', None)
    parser.parse_mbed_config('mbed_config.h', build_info)

    vlog('Copy files ...')
    export_files(dest, build_info.headers)
    export_files(dest, build_info.sources)
    shutil.copyfile(
        'BUILD/{}/GCC_ARM/.link_script.ld'.format(mbed_target),
        str(dest.joinpath('linker_script.ld')))

    all_library_info = make_all_library_info('mbed-os')
    use_libraries = [
        'targets',
        'platform',
        'rtos',
        'cmsis',
        'drivers',
        'events'
    ]

    unused_libraries = [
        x for x in all_library_info
        if x['name'] not in use_libraries]

    build_info = UnusedLibraryFilter().filterd(
        build_info, unused_libraries)

    # ----------------------------------------
    cmake_dir = dest.joinpath('CMake')
    mkdir_p(str(cmake_dir))

    b = build_info
    b.include_dirs = [Path(x).as_posix() for x in b.include_dirs]
    b.sources = [Path(x).as_posix() for x in b.sources]
    b.headers = [Path(x).as_posix() for x in b.headers]
    for x in b.removed_sources:
        x['value'] = Path(x['value']).as_posix()
    for x in b.removed_headers:
        x['value'] = Path(x['value']).as_posix()
    for x in b.removed_include_dirs:
        x['value'] = Path(x['value']).as_posix()

    args = {}
    args['project_name'] = dest.stem
    args['url'] = 'https://github.com/ARMmbed/mbed-os.git'
    args['tag'] = mbed_tag
    args['target'] = mbed_target
    args['warning_opts'] = build_info.warning_opts
    args['arch_opts'] = build_info.arch_opts
    args['c_extra_opts'] = build_info.c_extra_opts
    args['cxx_extra_opts'] = build_info.cxx_extra_opts
    args['include_dirs'] = build_info.include_dirs
    args['definitions'] = build_info.definitions
    args['link_libraries'] = build_info.link_libraries
    args['linker_flags'] = build_info.linker_flags
    args['sources'] = build_info.sources
    args['headers'] = build_info.headers
    args['config_definitions'] = build_info.config_definitions
    args['removed_sources'] = build_info.removed_sources
    args['removed_headers'] = build_info.removed_headers
    args['removed_config_definitions'] = build_info.removed_config_definitions
    args['removed_include_dirs'] = build_info.removed_include_dirs

    if verbose:
        vlog(pyaml.dump(args))

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
        'xmbedinit.log',
        'CMakeLists.txt',
        'main.cpp',
    ]
    render(args, dest, templates)


if __name__ == "__main__":
    main()
