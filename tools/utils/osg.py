"""
Specific functions working on the games.
"""

import re
import os
from difflib import SequenceMatcher
from utils import utils, constants as c

essential_fields = ('Home', 'State', 'Keywords', 'Code repository', 'Code language', 'Code license')
valid_fields = ('Home', 'Media', 'State', 'Play', 'Download', 'Platform', 'Keywords', 'Code repository', 'Code language',
'Code license', 'Code dependencies', 'Assets license', 'Developer', 'Build system', 'Build instructions')
valid_platforms = ('Windows', 'Linux', 'macOS', 'Android', 'iOS', 'Web')
recommended_keywords = ('action', 'arcade', 'adventure', 'visual novel', 'sports', 'platform', 'puzzle', 'role playing', 'simulation', 'strategy', 'card game', 'board game', 'music', 'educational', 'tool', 'game engine', 'framework', 'library', 'remake')
known_languages = ('AGS Script', 'ActionScript', 'Ada', 'AngelScript', 'Assembly', 'Basic', 'Blender Script', 'BlitzMax', 'C', 'C#', 'C++', 'Clojure', 'CoffeeScript', 'ColdFusion', 'D', 'DM', 'Dart', 'Dia', 'Elm', 'Emacs Lisp', 'F#', 'GDScript', 'Game Maker Script', 'Go', 'Groovy', 'Haskell', 'Haxe', 'Io', 'Java', 'JavaScript', 'Kotlin', 'Lisp', 'Lua', 'MegaGlest Script', 'MoonScript', 'None', 'OCaml', 'Objective-C', 'PHP', 'Pascal', 'Perl', 'Python', 'QuakeC', 'R', "Ren'py", 'Ruby', 'Rust', 'Scala', 'Scheme', 'Script', 'Shell', 'Swift', 'TorqueScript', 'TypeScript', 'Vala', 'Visual Basic', 'XUL', 'ZenScript', 'ooc')
known_licenses = ('2-clause BSD', '3-clause BSD', 'AFL-3.0', 'AGPL-3.0', 'Apache-2.0', 'Artistic License-1.0', 'Artistic License-2.0', 'Boost-1.0', 'CC-BY-NC-3.0', 'CC-BY-NC-SA-2.0', 'CC-BY-NC-SA-3.0', 'CC-BY-SA-3.0', 'CC-BY-NC-SA-4.0', 'CC-BY-SA-4.0', 'CC0', 'Custom', 'EPL-2.0', 'GPL-2.0', 'GPL-3.0', 'IJG', 'ISC', 'Java Research License', 'LGPL-2.0', 'LGPL-2.1', 'LGPL-3.0', 'MAME', 'MIT', 'MPL-1.1', 'MPL-2.0', 'MS-PL', 'MS-RL', 'NetHack General Public License', 'None', 'Proprietary', 'Public domain', 'SWIG license', 'Unlicense', 'WTFPL', 'wxWindows license', 'zlib')
known_multiplayer_modes = ('competitive', 'co-op', 'hotseat', 'LAN', 'local', 'massive', 'matchmaking', 'online', 'split-screen')

regex_sanitize_name = re.compile(r"[^A-Za-z 0-9-+]+")
regex_sanitize_name_space_eater = re.compile(r" +")


def name_similarity(a, b):
    return SequenceMatcher(None, str.casefold(a), str.casefold(b)).ratio()


def split_infos(infos):
    """
    Split into games, tools, frameworks, libraries
    """
    games = [x for x in infos if not any([y in x['keywords'] for y in ('tool', 'framework', 'library')])]
    tools = [x for x in infos if 'tool' in x['keywords']]
    frameworks = [x for x in infos if 'framework' in x['keywords']]
    libraries = [x for x in infos if 'library' in x['keywords']]
    return games, tools, frameworks, libraries


def entry_iterator():
    """

    """

    # get all entries (ignore everything starting with underscore)
    entries = os.listdir(c.entries_path)

    # iterate over all entries
    for entry in entries:
        entry_path = os.path.join(c.entries_path, entry)

        # ignore directories ("tocs" for example)
        if os.path.isdir(entry_path):
            continue

        # read entry
        content = utils.read_text(entry_path)

        # yield
        yield entry, entry_path, content


def canonical_entry_name(name):
    """
    Derives a canonical game name from an actual game name (suitable for file names, ...)
    """
    name = name.casefold()
    name = name.replace('ö', 'o').replace('ä', 'a').replace('ü', 'u')
    name = regex_sanitize_name.sub('', name)
    name = regex_sanitize_name_space_eater.sub('_', name)
    name = name.replace('_-_', '-')
    name = name.replace('--', '-').replace('--', '-')

    return name


def parse_entry(content):
    """
    Returns a dictionary of the features of the content.

    Raises errors when a major error in the structure is expected, prints a warning for minor errors.
    """

    info = {}

    # read name
    regex = re.compile(r"^# (.*)") # start of content, starting with "# " and then everything until the end of line
    matches = regex.findall(content)
    if len(matches) != 1 or not matches[0]: # name must be there
        raise RuntimeError('Name not found in entry "{}" : {}'.format(content, matches))
    info['name'] = matches[0]

    # read description
    regex = re.compile(r"^.*\n\n_(.*)_\n") # third line from top, everything between underscores
    matches = regex.findall(content)
    if len(matches) != 1 or not matches[0]: # description must be there
        raise RuntimeError('Description not found in entry "{}"'.format(content))
    info['description'] = matches[0]

    # first read all field names
    regex = re.compile(r"^- (.*?): ", re.MULTILINE) # start of each line having "- ", then everything until a colon, then ": "
    fields = regex.findall(content)

    # check that essential fields are there
    for field in essential_fields:
        if field not in fields: # essential fields must be there
            raise RuntimeError('Essential field "{}" missing in entry "{}"'.format(field, info['name']))

    # check that all fields are valid fields and are existing in that order
    index = 0
    for field in fields:
        while index < len(valid_fields) and field != valid_fields[index]:
            index += 1
        if index == len(valid_fields): # must be valid fields and must be in the right order
            raise RuntimeError('Field "{}" in entry "{}" either misspelled or in wrong order'.format(field, info['name']))

    # iterate over found fields
    for field in fields:
        regex = re.compile(r"- {}: (.*)".format(field))
        matches = regex.findall(content)
        if len(matches) != 1: # every field must be present only once
            raise RuntimeError('Field "{}" in entry "{}" exist multiple times.'.format(field, info['name']))
        v = matches[0]

        # first store as is
        info[field.lower()+'-raw'] = v

        # remove parenthesis with content
        v = re.sub(r'\([^)]*\)', '', v)

        # split on ', '
        v = v.split(', ')

        # strip
        v = [x.strip() for x in v]

        # remove all being false (empty) that were for example just comments
        v = [x for x in v if x]

        # if entry is of structure <..> remove <>
        v = [x[1:-1] if x[0] is '<' and x[-1] is '>' else x for x in v]

        # empty fields will not be stored
        if not v:
            continue

        # store in info
        info[field.lower()] = v

    # check again that essential fields made it through
    for field in ('home', 'state', 'keywords', 'code language', 'code license'):
        if field not in info: # essential fields must still be inside
            raise RuntimeError('Essential field "{}" empty in entry "{}"'.format(field, info['name']))

    # now checks on the content of fields

    # name should not have spaces at the begin or end
    v = info['name']
    if len(v) != len(v.strip()): # warning about that
        print('Warning: No leading or trailing spaces in the entry name, "{}"'.format(info['name']))

    # state (essential field) must contain either beta or mature but not both, but at least one
    v = info['state']
    for t in v:
        if t != 'beta' and t != 'mature' and not t.startswith('inactive since '):
            raise RuntimeError('Unknown state tage "{}" in entry "{}"'.format(t, info['name']))
    if 'beta' in v != 'mature' in v:
        raise RuntimeError('State must be one of <"beta", "mature"> in entry "{}"'.format(info['name']))

    # extract inactive year
    phrase = 'inactive since '
    inactive_year = [x[len(phrase):] for x in v if x.startswith(phrase)]
    assert len(inactive_year) <= 1
    if inactive_year:
        info['inactive'] = inactive_year[0]

    # urls in home, download, play and code repositories must start with http or https (or git) and should not contain spaces
    for field in ['home', 'download', 'play', 'code repository']:
        if field in info:
            for url in info[field]:
                if not any([url.startswith(x) for x in ['http://', 'https://', 'git://', 'svn://', 'ftp://', 'bzr://']]):
                    raise RuntimeError('URL "{}" in entry "{}" does not start with http/https/git/svn/ftp/bzr'.format(url, info['name']))
                if ' ' in url:
                    raise RuntimeError('URL "{}" in entry "{}" contains a space'.format(url, info['name']))

    # github/gitlab repositories should end on .git and should start with https
    if 'code repository' in info:
        for repo in info['code repository']:
            if any((x in repo for x in ('github', 'gitlab', 'git.tuxfamily', 'git.savannah'))):
                if not repo.startswith('https://'):
                    print('Warning: Repo {} in entry "{}" should start with https://'.format(repo, info['name']))
                if not repo.endswith('.git'):
                    print('Warning: Repo {} in entry "{}" should end on .git.'.format(repo, info['name']))

    # check that all platform tags are valid tags and are existing in that order
    if 'platform' in info:
        index = 0
        for platform in info['platform']:
            while index < len(valid_platforms) and platform != valid_platforms[index]:
                index += 1
            if index == len(valid_platforms): # must be valid platforms and must be in that order
                raise RuntimeError('Platform tag "{}" in entry "{}" either misspelled or in wrong order'.format(platform, info['name']))

    # there must be at least one keyword
    if 'keywords' not in info:
        raise RuntimeError('Need at least one keyword in entry "{}"'.format(info['name']))

    # check for existence of at least one recommended keywords
    fail = True
    for recommended_keyword in recommended_keywords:
        if recommended_keyword in info['keywords']:
            fail = False
            break
    if fail: # must be at least one recommended keyword
        raise RuntimeError('Entry "{}" contains no recommended keyword'.format(info['name']))

    # languages should be known
    languages = info['code language']
    for language in languages:
        if language not in known_languages:
            print('Warning: Language {} in entry "{}" is not a known language. Misspelled or new?'.format(language, info['name']))

    # licenses should be known
    licenses = info['code license']
    for license in licenses:
        if license not in known_licenses:
            print('Warning: License {} in entry "{}" is not a known license. Misspelled or new?'.format(license, info['name']))

    return info


def assemble_infos():
    """
    Parses all entries and assembles interesting infos about them.
    """

    print('assemble game infos')

    # a database of all important infos about the entries
    infos = []

    # iterate over all entries
    for entry, _, content in entry_iterator():

        # parse entry
        info = parse_entry(content)

        # add file information
        info['file'] = entry

        # check canonical file name
        canonical_file_name = canonical_entry_name(info['name']) + '.md'
        # we also allow -X with X =2..9 as possible extension (because of duplicate canonical file names)
        if canonical_file_name != entry and canonical_file_name != entry[:-5] + '.md':
            print('Warning: file {} should be {}'.format(entry, canonical_file_name))
            source_file = os.path.join(c.entries_path, entry)
            target_file = os.path.join(c.entries_path, canonical_file_name)
            if not os.path.isfile(target_file):
                pass
                # os.rename(source_file, target_file)

        # add to list
        infos.append(info)

    return infos


def extract_links():
    """
    Parses all entries and extracts http(s) links from them
    """

    # regex for finding urls (can be in <> or in ]() or after a whitespace
    regex = re.compile(r"[\s\n]<(http.+?)>|\]\((http.+?)\)|[\s\n](http[^\s\n,]+?)[\s\n,]")

    # iterate over all entries
    urls = set()
    for _, _, content in entry_iterator():

        # apply regex
        matches = regex.findall(content)

        # for each match
        for match in matches:

            # for each possible clause
            for url in match:

                # if there was something (and not a sourceforge git url)
                if url:
                    urls.add(url)
    urls = sorted(list(urls), key=str.casefold)
    return urls
