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

See [WRITING_DOCS](WRITING_DOCS.md) for an explanation of the syntax.
