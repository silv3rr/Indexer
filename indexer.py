#!/usr/bin/env python3

"""
Indexer v.1.0.1
Author: Josh Brunty (josh dot brunty at marshall dot edu)
DESCRIPTION: This script generates an .html index  of files within a directory (recursive is OFF by default). Start from current dir or from folder passed as first positional argument. Optionally filter by file types with --filter "*.py".
-handle symlinked files and folders: displayed with custom icons
By default only the current folder is processed.
Use -r or --recursive to process nested folders.
"""

# Indexer v.1.0.2-slv (2023-06-19)
# CHANGES:
# - make output look more like apache autoindex
# - parse htaccess
# - added list of files to ignore
# - added optional custom index entry
# - moved css and svg to separate files
# - added files to include in index
# - adds content from svg, header, footer etc files
# - added kludge to replace href in subdirs

import argparse
import datetime
import os
import sys
from pathlib import Path
from urllib.parse import quote

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))
WORKDIR = os.getcwd()

# CONFIGURATION:

DEFAULT_OUTPUT_FILE = 'index.html'

INDEX_IGNORE = [
    '.git', '.js', '.log', '.swp', 'rescan', 'rescan.txt',
    'LINKS', 'CNAME', 'README', 'favicon.ico', 'assets', 'index.html', 'robots.txt',
    'Gemfile', 'Gemfile.lock', '404.html', 'about.markdown', 'index.markdown', 'index.md', 'scripts', 'vendor',
]

INCLUDE_FILES = [
         { 'htaccess': f'{WORKDIR}/.htaccess' },
         { 'svg': f'{SCRIPTDIR}/indexer.svg' },
         { 'header': f'{WORKDIR}/_includes/header.html' },
         { 'footer': f'{WORKDIR}/_includes/footer1.html' },
]

# add one or more entries to index
CUSTOM_INDEX = [
    #{ "href: "/some/example/path" }", "icon": "#svg-id", "name": "example-name", "description": "bla bla"},
    { "href": "LINKS", "icon": "#folder-shortcut", "name": "LINKS", "description": "LINKS: other websites with scripts, repos and mirrors"}
]
# if set to False, dont point go-up link to '..' for top index (only subdirs)
TOPDIR_UP = True

# kludge: if top_dir matches SUBDIR, change href's to '../<path>' and replace strings in index
SUBDIRS = [ '/ARCHIVE' ]
SUBDIR_REPLACE = [
        ['="assets/', '="../assets/'],
        ['README.md', '../README.md'],
        ['favicon.ico', '../favicon.ico']
]


HTACCESS_MAPPING = CONTENT = FILES_OBJ = {}
if 'CUSTOM_INDEX' not in globals():
    CUSTOM_INDEX = []
CONTENT['custom_index'] = CUSTOM_INDEX
for f in INCLUDE_FILES:
    for name, path in f.items():
        with open(path, 'r', encoding='utf-8', errors='ignore') as FILES_OBJ[path]:
            if name == 'htaccess':
                CONTENT['htaccess'] = FILES_OBJ[path].readlines()
                for line in CONTENT['htaccess']:
                    if line.startswith('AddDescription'):
                        HTACCESS_MAPPING[line.split()[-1]] = ' '.join(line.split()[1:-1])
            else:
                CONTENT[name] = FILES_OBJ[path].read()


def process_dir(top_dir, opts, content):
    """ creates index file for path """
    glob_patt = opts.filter or '*'

    path_top_dir: Path
    path_top_dir = Path(top_dir)
    index_file = None

    index_path = Path(path_top_dir, opts.output_file)

    if opts.verbose:
        print(f'Traversing dir {path_top_dir.absolute()}')

    try:
        index_file = open(index_path, 'w', encoding='utf-8')
    except Exception as e:
        print('cannot create file %s %s' % (index_path, e))
        return

    go_up = False
    if TOPDIR_UP:
        go_up = True
    if any(i in f'{path_top_dir.absolute()}' for i in SUBDIRS):
        for old, new in SUBDIR_REPLACE:
            if opts.verbose:
                print(f"Subdir: replacing '{old}' -> '{new}'")
            content['header'] = content['header'].replace(old, new)
        for i in content['custom_index']:
            href = i.get('href')
            if href:
                i.update(href = f'../{href}')
        go_up = True

    if content['header']:
        if opts.verbose:
            print("Adding header")
        index_file.write(content['header'])

    if content['svg']:
        if opts.verbose:
            print("Adding svg")
        index_file.write(content['svg'])
    index_file.write("""
        <header></header>
        <main>
        <div class="listing">
            <table aria-describedby="summary">
                <thead>
                    <tr>
                        <th></th>
                        <th>Name</th>
                        <th>Description</th>
                        <th>Size</th>
                        <th class="hideable">
                            Modified
                        </th>
                        <th class="hideable"></th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="clickable">
                        <td></td>
                        <td>
                            <a href=\""""f'{".." if go_up else "."}'"""\"><svg width="1.5em" height="1em" version="1.1" viewBox="0 0 24 24"><use xlink:href="#go-up"></use></svg>
                            <span class="goup">..</span></a>
                        </td>
                        <td>&mdash;</td>
                        <td>&mdash;</td>
                        <td class="hideable">&mdash;</td>
                        <td class="hideable"></td>
                    </tr>
    """)
    if content['custom_index']:
        for i in content['custom_index']:
            if opts.verbose:
                print("Adding custom_index")
            index_file.write("""
                        <tr class="clickable" """f'{"style=display:none;" if len(i) == 0 else ""}'""">
                            <td></td>
                            <td>
                                <a href=\""""f'{i.get("href")}'"""\">
                                <svg width="1.5em" height="1em" version="1.1" viewBox="0 0 265 323"><use xlink:href=\""""f'{i.get("icon")}'"""\"></use></svg>
                                <span class="goup">"""f'{i.get("name")}'"""</span></a>
                            </td>
                            <td>"""f'{i.get("description")}'"""</td>
                            <td>&mdash;</td>
                            <td class="hideable">&mdash;</td>
                            <td class="hideable"></td>
                        </tr>
            """)

    # sort dirs first
    sorted_entries = sorted(path_top_dir.glob(glob_patt), key=lambda p: (p.is_file(), p.name))

    entry: Path
    for entry in sorted_entries:

        # don't include index.html in the file listing
        if entry.name.lower() == opts.output_file.lower():
            continue

        # don't include entries starting with . or _ or listed in INDEX_IGNORE
        if entry.name.startswith('.') or entry.name.startswith('_') or any(i in entry.name for i in INDEX_IGNORE):
            if opts.verbose:
                print(f"Ignoring '{entry.name}'")
            continue

        if entry.is_dir() and opts.recursive:
            process_dir(entry, opts, content)

        # From Python 3.6, os.access() accepts path-like objects
        if (not entry.is_symlink()) and not os.access(str(entry), os.W_OK):
            print(f"*** WARNING *** entry {entry.absolute()} is not writable! SKIPPING!")
            continue
        if opts.verbose:
            print(f'{entry.absolute()}')

        size_bytes = -1  ## is a folder
        size_pretty = '&mdash;'
        last_modified = '-'
        last_modified_human_readable = '-'
        last_modified_iso = ''
        description = ''
        try:
            if entry.is_file():
                size_bytes = entry.stat().st_size
                size_pretty = pretty_size(size_bytes)

            if entry.is_dir() or entry.is_file():
                last_modified = datetime.datetime.fromtimestamp(entry.stat().st_mtime).replace(microsecond=0)
                last_modified_iso = last_modified.isoformat()
                #last_modified_human_readable = last_modified.strftime("%c")
                last_modified_human_readable = last_modified.strftime("%F %T")

        except Exception as e:
            print('ERROR accessing file name:', e, entry)
            continue

        entry_path = str(entry.name)

        if entry.is_dir() and not entry.is_symlink():
            entry_type = 'folder'
            if os.name not in ('nt',):
                # append trailing slash to dirs, unless it's windows
                entry_path = os.path.join(entry.name, '')
        elif entry.is_dir() and entry.is_symlink():
            entry_type = 'folder-shortcut'
            print('dir-symlink', entry.absolute())

        elif entry.is_file() and entry.is_symlink():
            entry_type = 'file-shortcut'
            print('file-symlink', entry.absolute())
        else:
            entry_type = 'file'

        description = "&mdash;"

        if HTACCESS_MAPPING.get('/'.join(entry.parts[-2:])):
            description = HTACCESS_MAPPING.get('/'.join(entry.parts[-2:]))
        elif HTACCESS_MAPPING.get(entry.name):
            description = HTACCESS_MAPPING.get(entry.name)
        description = description.lstrip('"').strip('"')

        index_file.write(f"""
            <tr class="file">
                <td></td>
                <td>
                    <a href="{quote(entry_path)}">
                        <svg width="1.5em" height="1em" version="1.1" viewBox="0 0 265 323"><use xlink:href="#{entry_type}"></use></svg>
                        <span class="name">{entry.name}</span>
                    </a>
                </td>
                <td>{description}</td>
                <td data-order="{size_bytes}">{size_pretty}</td>
                <td class="hideable"><time datetime="{last_modified_iso}">{last_modified_human_readable}</time></td>
                <td class="hideable"></td>
            </tr>
        """)

    index_file.write("""
                </tbody>
            </table>
        </div>
        <footer/>
        </main>
    """)
    if content['footer']:
        if opts.verbose:
            print("Adding footer")
        index_file.write(content['footer'])
    if index_file:
        index_file.close()


# bytes pretty-printing
UNITS_MAPPING = [
    (1024 ** 5, ' PB'),
    (1024 ** 4, ' TB'),
    (1024 ** 3, ' GB'),
    (1024 ** 2, ' MB'),
    (1024 ** 1, ' KB'),
    (1024 ** 0, (' byte', ' bytes')),
]


def pretty_size(f_bytes, units=UNITS_MAPPING):
    """Human-readable file sizes.
    ripped from https://pypi.python.org/pypi/hurry.filesize/
    """
    for factor, suffix in units:
        if f_bytes >= factor:
            break
    amount = int(f_bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''DESCRIPTION: This script generates an .html index  of files within a directory (recursive is OFF by default). Start from current dir or from folder passed as first positional argument. Optionally filter by file types with --filter "*.py"
Email josh dot brunty at marshall dot edu for additional help. ''')

    parser.add_argument('top_dir',
                        nargs='?',
                        action='store',
                        help='top folder from which to start generating indexes, '
                             'use current folder if not specified',
                        default=os.getcwd())

    parser.add_argument('--filter', '-f',
                        help='only include files matching glob',
                        required=False)

    parser.add_argument('--output-file', '-o',
                        metavar='filename',
                        default=DEFAULT_OUTPUT_FILE,
                        help=f'Custom output file, by default "{DEFAULT_OUTPUT_FILE}"')

    parser.add_argument('--recursive', '-r',
                        action='store_true',
                        help="recursively process nested dirs (FALSE by default)",
                        required=False)

    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='***WARNING: can take longer time with complex file tree structures on slow terminals***'
                             ' verbosely list every processed file',
                        required=False)

    config = parser.parse_args(sys.argv[1:])
    process_dir(config.top_dir, config, CONTENT)
