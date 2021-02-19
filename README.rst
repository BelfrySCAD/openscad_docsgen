################################
OpenSCAD Documentation Generator
################################

This package generates wiki-ready GitHub flavored markdown documentation pages from in-line source
code comments.  This is similar to Doxygen or JavaDoc, but designed for use with OpenSCAD code.
Example images can be generated automatically from short example scripts.

Documentation about how to add documentation comments to OpenSCAD code can be found at
`https://github.com/revarbat/openscad_docsgen/blob/main/WRITING_DOCS.rst`


Using openscad-docsgen
----------------------

The simplest way to generate documentation is::

    % openscad_docsgen *.scad

Which will read all of .scad files in the current directory, and writes out documentation to the ``./docs/`` dir.
To write out to a different directory, use the ``-D`` argument::

    % openscad_docsgen -D wikidir *.scad

To write out an alphabetical function/module index markdown file, use the ``-i`` flag::

    % openscad_docsgen -i *.scad

To write out a Table of Contents markdown file, use the ``-t`` flag::

    % openscad_docsgen -t *.scad

To write out a CheatSheet markdown file, use the ``-c`` flag::

    % openscad_docsgen -c *.scad


