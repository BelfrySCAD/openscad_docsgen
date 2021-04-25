################################
OpenSCAD Documentation Generator
################################

This package generates wiki-ready GitHub flavored markdown documentation pages from in-line source
code comments.  This is similar to Doxygen or JavaDoc, but designed for use with OpenSCAD code.
Example images can be generated automatically from short example scripts.

Documentation about how to add documentation comments to OpenSCAD code can be found at
`https://github.com/revarbat/openscad_docsgen/blob/main/WRITING_DOCS.md`


Installing openscad-docsgen
---------------------------

The easiest way to install this is to use pip::

    % pip3 install openscad-docsgen
    
To install directly from these sources, you can instead do::

    % python3 setup.py build install


Using openscad-docsgen
----------------------

The simplest way to generate documentation is::

    % openscad-docsgen -m *.scad

Which will read all of .scad files in the current directory, and writes out documentation to
the ``./docs/`` dir.  To write out to a different directory, use the ``-D`` argument::

    % openscad-docsgen -D wikidir -m *.scad

To write out an alphabetical function/module index markdown file, use the ``-i`` flag::

    % openscad-docsgen -i *.scad

To write out a Table of Contents markdown file, use the ``-t`` flag::

    % openscad-docsgen -t *.scad

To write out a CheatSheet markdown file, use the ``-c`` flag::

    % openscad-docsgen -c *.scad
    
You can just test for script errors more quickly with the ``-T`` flag (for test-only)::

    % openscad-docsgen -T *.scad


Configuration File
------------------
You can also make more persistent configurations by putting a `.openscad_docsgen_rc` file in the
directory you will be running openscad-docsgen from.  It can look something like this::

    DocsDirectory: WikiDir/
    IgnoreFiles:
      foo.scad
      std.scad
      version.scad
      tmp_*.scad
    PrioritizeFiles:
      First.scad
      Second.scad
      Third.scad
      Fourth.scad
    DefineHeader(BulletList): Side Effects
    DefineHeader(Table:Anchor&nbsp;Name|Position): Extra Anchors

For an explanation of the syntax and the specific headers, see:
`https://github.com/revarbat/openscad_docsgen/blob/main/WRITING_DOCS.md`

External Calling
----------------
Here's an example of how to use this library, to get the parsed documentation data::

    import openscad_docsgen as docsgen
    from glob import glob
    from pprint import pprint
    dgp = docsgen.DocsGenParser(quiet=True)
    dgp.parse_files(glob("*.scad"))
    for name in dgp.get_indexed_names():
        data = dgp.get_indexed_data(name)
        print(name)
        print(data["description"])

The data for an OpenSCAD function, module, or constant generally looks like::

    {
        'name': 'Function&Module',  // Could also be 'Function', 'Module', or 'Constant'
        'subtitle': 'line_of()',
        'body': [],
        'file': 'distributors.scad',
        'line': 43,
        'aliases': ['linear_spread()'],
        'topics': ['Distributors'],
        'usages': [
            {
                'subtitle': 'Spread `n` copies by a given spacing',
                'body': ['line_of(spacing, <n>, <p1=>) ...']
            },
            {
                'subtitle': 'Spread copies every given spacing along the line',
                'body': ['line_of(spacing, <l=>, <p1=>) ...']
            },
            {
                'subtitle': 'Spread `n` copies along the length of the line',
                'body': ['line_of(<n=>, <l=>, <p1=>) ...']
            },
            {
                'subtitle': 'Spread `n` copies along the line from `p1` to `p2`',
                'body': ['line_of(<n=>, <p1=>, <p2=>) ...']
            },
            {
                'subtitle': 'Spread copies every given spacing, centered along the line from `p1` to `p2`',
                'body': ['line_of(<spacing>, <p1=>, <p2=>) ...']
            },
            {
                'subtitle': 'As a function',
                'body': [
                    'pts = line_of(<spacing>, <n>, <p1=>);',
                    'pts = line_of(<spacing>, <l=>, <p1=>);',
                    'pts = line_of(<n=>, <l=>, <p1=>);',
                    'pts = line_of(<n=>, <p1=>, <p2=>);',
                    'pts = line_of(<spacing>, <p1=>, <p2=>);'
                ]
            }
        ],
        'description': [
            'When called as a function, returns a list of points at evenly spread positions along a line.',
            'When called as a module, copies `children()` at one or more evenly spread positions along a line.',
            'By default, the line will be centered at the origin, unless the starting point `p1` is given.',
            'The line will be pointed towards `RIGHT` (X+) unless otherwise given as a vector in `l`,',
            '`spacing`, or `p1`/`p2`.',
        ],
        'arguments': [
            'spacing = The vector giving both the direction and spacing distance between each set of copies.',
            'n = Number of copies to distribute along the line. (Default: 2)',
            '---',
            'l = Either the scalar length of the line, or a vector giving both the direction and length of the line.',
            'p1 = If given, specifies the starting point of the line.',
            'p2 = If given with `p1`, specifies the ending point of line, and indirectly calculates the line length.'
        ],
        'see_also': ['xcopies()', 'ycopies()'],
        'examples': [
            ['line_of(10) sphere(d=1);'],
            ['line_of(10, n=5) sphere(d=1);'],
            ['line_of([10,5], n=5) sphere(d=1);'],
            ['line_of(spacing=10, n=6) sphere(d=1);'],
            ['line_of(spacing=[10,5], n=6) sphere(d=1);'],
            ['line_of(spacing=10, l=50) sphere(d=1);'],
            ['line_of(spacing=10, l=[50,30]) sphere(d=1);'],
            ['line_of(spacing=[10,5], l=50) sphere(d=1);'],
            ['line_of(l=50, n=4) sphere(d=1);'],
            ['line_of(l=[50,-30], n=4) sphere(d=1);'],
            [
                'line_of(p1=[0,0,0], p2=[5,5,20], n=6) '
                'cube(size=[3,2,1],center=true);'
            ],
            [
                'line_of(p1=[0,0,0], p2=[5,5,20], spacing=6) '
                'cube(size=[3,2,1],center=true);'
            ],
            [
                'line_of(l=20, n=3) {',
                '    cube(size=[1,3,1],center=true);',
                '    cube(size=[3,1,1],center=true);',
                '}'
            ],
            [
                'pts = line_of([10,5],n=5);',
                'move_copies(pts) circle(d=2);'
            ]
        ],
        'children': [
            {
                'name': 'Side Effects',
                'subtitle': '',
                'body': [
                    '`$pos` is set to the relative centerpoint of each child copy.',
                    '`$idx` is set to the index number of each child being copied.'
                ],
                'file': 'distributors.scad',
                'line': 88
            }
        ]
    }


