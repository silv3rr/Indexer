#!/usr/bin/env python3

# Indexer v.1.0.2-slv
# Author: Josh Brunty (josh dot brunty at marshall dot edu)
# DESCRIPTION: This script generates an .html index  of files within a directory (recursive is OFF by default). Start from current dir or from folder passed as first positional argument. Optionally filter by file types with --filter "*.py". 

# -handle symlinked files and folders: displayed with custom icons
# By default only the current folder is processed.
# Use -r or --recursive to process nested folders.

# 2023-06-19 Changes slv: added some stuff and custom index entry to make this more work like apache autoindex

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
    'LINKS', 'CNAME', 'README.md', 'favicon.ico', 'assets', 'index.html', 'robots.txt', 'scripts'
]
FILES = [
         { 'htaccess': f'{WORKDIR}/.htaccess' },
         { 'svg': f'{SCRIPTDIR}/indexer.svg' },
         { 'header': f'{WORKDIR}/_includes/header.html' },
         { 'footer': f'{WORKDIR}/_includes/footer1.html' },
]

# add entry(s) to index
CUSTOM_INDEX = [
    { "href": "LINKS", "icon": "#folder-shortcut", "name": "LINKS", "description": "LINKS: other websites with scripts, repos and mirrors"}
]

# in top_dir matches SUBDIR, change href's to '../<path>'
SUBDIR = '/ARCHIVE'

# for FIX_PATH, search/replace strings in index
SEARCH_REPLACE = [
        ['="assets/', '="../assets/'], 
        ['README.md', '../README.md'],
        ['favicon.ico', '../favicon.ico']
]


FILES_CONTENT = FILES_OBJ = {}
for f in FILES:
    for name, path in f.items():
        with open(path, 'r', encoding='utf-8', errors='ignore') as FILES_OBJ[path]:
            if name == 'htaccess':
                FILES_CONTENT['htaccess'] = FILES_OBJ[path].readlines()
            else:
                FILES_CONTENT[name] = FILES_OBJ[path].read()

HTACCESS_MAP = {}
for line in FILES_CONTENT['htaccess']:
    if line.startswith('AddDescription'):
        HTACCESS_MAP[line.split()[-1]] = ' '.join(line.split()[1:-1])

if 'CUSTOM_INDEX' not in globals():
    CUSTOM_INDEX = []

def process_dir(top_dir, opts, content, custom_index):
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
    if SUBDIR in f'{path_top_dir.absolute()}':
        for old, new in SEARCH_REPLACE:
            content['header'] = content['header'].replace(old, new)
        for i in custom_index:
            href = i.get('href')
            if href:
                i.update(href = f'../{href}')
        go_up = True
    index_file.write(content['header'])
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
    for i in custom_index:
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
        if entry.name.startswith('.') or entry.name.startswith('_') or entry.name in INDEX_IGNORE:
            continue

        if entry.is_dir() and opts.recursive:
            process_dir(entry, opts, header, custom_index)

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

        if HTACCESS_MAP.get('/'.join(entry.parts[-2:])):
            description = HTACCESS_MAP.get('/'.join(entry.parts[-2:]))
        elif HTACCESS_MAP.get(entry.name):
            description = HTACCESS_MAP.get(entry.name)
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


def pretty_size(bytes, units=UNITS_MAPPING):
    """Human-readable file sizes.
    ripped from https://pypi.python.org/pypi/hurry.filesize/
    """
    for factor, suffix in units:
        if bytes >= factor:
            break
    amount = int(bytes / factor)

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
    process_dir(config.top_dir, config, FILES_CONTENT, CUSTOM_INDEX)
