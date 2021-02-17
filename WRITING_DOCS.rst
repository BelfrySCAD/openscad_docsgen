Formatting Comments for Documenting OpenSCAD Code
=================================================

Documentation blocks are all based around a single simple syntax::

    // Block Name(Metadata): TitleText
    //   Body line 1
    //   Body line 2
    //   Body line 3

- The Block Name is one or two words, both starting with a capital letter.
- The Metadata is in parentheses.  It is optional, and can contain fairly arbitrary
  text, as long as it doesn't include newlines or parentheses. If the Metadata part
  is not given, the parentheses are optional.
- A colon ``:`` will always follow after the Block Name and optional Metadata.
- The TitleText will be preceded by a space `` ``, and can contain arbitrary text,
  as long as it contains no newlines.  The TitleText part is also optional for
  some header blocks.
- The body will contain zero or more lines of text indented by three spaces ``   ``
  after the comment markers.  Each line can contain arbitrary text.

So, for example, a Figure block to show a 640x480 animated GIF of a spinning
shape may look like::

    // Figure(Spin,Size=640x480,VPD=444): A Cube and Cylinder.
    //   cube(80, center=true);
    //   cylinder(h=100,d=60,center=true);

Various block types don't need all of those parts, so they may look simpler::

    // Topics: Mask, Cylindrical, Attachable

Or::

    // Description:
    //   This is a description.
    //   It can be multiple lines in length.

Or::

    // Usage: Typical Usage
    //   x = foo(a, b, c);
    //   x = foo([a, b, c, ...]);

Comments blocks that don't start with a known block header are ignored and not
added to output documentation.  This lets you have normal comments in your
code that are not used for documentation.  If you must start a comment block
with one of the known headers, then adding a single extra ``/`` or space
after the comment marker, will make it be treated as a regular comment::

    /// File: Foobar.scad


Block Headers
=======================

File/LibFile Blocks
-------------------

All files must have either a ``// File:`` block or a ``// LibFile:`` block at the
start.  This is the place to put in the canonical filename, and a description
of what the file is for.  These blocks can be used interchangably, but you can
only have one per file.  ``// File:`` or ``// LibFile:`` blocks can be followed
by a multiple line body that are added as markdown text after the header::

    // LibFile: foo.scad
    //   You can have several lines of markdown formatted text here.
    //   You just need to make sure that each line is indented, with
    //   at least three spaces after the comment marker.  You can
    //   denote a paragraph break with a comment line with three
    //   trailing spaces, or just a period.
    //   .
    //   The end of the block is denoted by a line without a comment.

Or::

    // File: Foobar.scad
    //   This file contains a collection of metasyntactical nonsense.

Includes Block
--------------

To declare what code the user needs to add to their code to include or use this
library file, you can use the ``// Includes:`` block.  This code block will also
be prepended to all Example and Figure code blocks before they are evaluated::

    // Includes:
    //   include <BOSL2/std.scad>
    //   include <BOSL2/std.scad>

CommonCode Block
----------------

If you have a block of code you plan to use throughout the file's Figure or
Example blocks, and you don't actually want it displayed, you can use a
``// CommonCode:`` block like thus::

    // CommonCode:
    //   module text3d(text, h=0.01, size=3) {
    //       linear_extrude(height=h, convexity=10) {
    //           text(text=text, size=size, valign="center", halign="center");
    //       }
    //   }

Then you can use that code in later examples::

    // Example:
    //   text3d("Foobar");


Section Block
-------------
Section blocks take a title, and an optional body that will be shown as the
description of the Section.  If a body line if just a ``.`` (dot, period), then
that line is treated as a blank line in the output::

    // Section: Foobar
    //   You can have several lines of markdown formatted text here.
    //   You just need to make sure that each line is indented, with
    //   at least three spaces after the comment marker.  You can
    //   denote a paragraph break with a comment line with three
    //   trailing spaces, or just a period.
    //   .
    //   The end of the block is denoted by a line without a comment.
    //   or a line that is unindented after the comment.

Sections can also include Figures; images generated from code that is not shown
in a code block.


Item Blocks
-----------

Item blocks headers come in four varieties: ``Constant``, ``Function``,
``Module``, and ``Function&Module``.

The ``Constant`` header is used to document a code constant.  It should have
a Description sub-block, and Example sub-blocks are recommended::

    // Constant: PHI
    // Description: The golden ratio phi.
    PHI = (1+sqrt(5))/2;


The ``Module`` header is used to document a module.  It should have a
Description sub-block. It is recommended to also have Usage, Arguments, and
Example/Examples sub-blocks::

    // Module: cross()
    // Usage:
    //   cross(size);
    // Description:
    //   Creates a 2D cross/plus shape.
    // Arguments:
    //   size = The scalar size of the cross from tip to tip in both axes.
    // Example(2D):
    //   cross(size=100);
    module cross(size=1) {
        square([size, size/3], center=true);
        square([size/3, size], center=true);
    }


The ``Function`` header is used to document a function.  It should have a
Description sub-block. It is recommended to also have Usage, Arguments, and
Example/Examples sub-blocks.  By default, Examples will not generate images
for function blocks::

    // Function: vector_angle()
    // Usage:
    //   ang = vector_angle(v1, v2);
    // Description:
    //   Calculates the angle between two vectors in degrees.
    // Arguments:
    //   v1 = The first vector.
    //   v2 = The second vector.
    // Example:
    //   v1 = [1,1,0];
    //   v2 = [1,0,0];
    //   angle = vector_angle(v1, v2);
    //   // Returns: 45
    function vector_angle(v1,v2) =
	acos(max(-1,min(1,(vecs[0]*vecs[1])/(norm0*norm1))));
        

The ``Function&Module`` header is used to document a function which has a
related module of the same name.  It should have a Description sub-block.  It
is recommended to also have Usage, Arguments, and Example/Examples sub-blocks.
You should have Usage blocks for both calling as a function, and calling as a
module::

    // Function&Module: oval()
    // Topics: 2D Shapes, Geometry
    // Usage: As a Module
    //   oval(rx,ry);
    // Usage: As a Function
    //   path = oval(rx,ry);
    // Description:
    //   When called as a function, returns the perimeter path of the oval.
    //   When called as a module, creates a 2D oval shape.
    // Arguments:
    //   rx = X axis radius.
    //   ry = Y axis radius.
    // Example(2D): Called as a Function
    //   path = oval(100,60);
    //   polygon(path);
    // Example(2D): Called as a Module
    //   oval(80,60);
    module oval(rx,ry) {
        polygon(oval(rx,ry));
    }
    function oval(rx,ry) =
        [for (a=[360:-360/$fn:0.0001]) [rx*cos(a),ry*sin(a)];


These Type blocks can have a number of sub-blocks.  Most sub-blocks are
optional,  The available standard sub-blocks are:

- `// Status: DEPRECATED`
- `// Topics: Comma, Delimited, Topic, List`
- `// Usage:`
- `// Description:`
- `// Arguments:`
- `// Figure:` or `// Figures`
- `// Example:` or `// Examples:`


Status Block
------------

The Status block is used to mark a function or module as deprecated::

    // Status: DEPRECATED, use foo() instead


Topics Block
------------

The Topics block can associate various topics with the current function or
module.  This can be used to make an index of Topics::

    // Topics: 2D Shapes, Geometry, Masks


Usage Block
-----------

The Usage block describes the various ways that the current function or module
can be called, with the names of the arguments.  By convention, the first few
arguments that can be called positionally just have their name shown.  The
remaining arguments that should be passed by name, will have the name followed
by an ``=`` (equal sign).  Arguments that are optional in the given Usage context
are shown in ``<`` and ``>`` angle brackets::

    // Usage: As a Module
    //   oval(rx, ry, <spin=>);
    // Usage: As a Function
    //   path = oval(rx, ry, <spin=>);


Description Block
-----------------

The Description block just describes the currect function, module, or constant::

    // Descripton: This is the description for this function or module.
    //   It can be multiple lines long.  Markdown syntax code will be used
    //   verbatim in the output markdown file, with the exception of `_`,
    //   which will traslate to `\_`, so that underscores in function/module
    //   names don't get butchered.


Arguments Block
---------------

The Arguments block creates a table that describes the positional arguments
for a function or module, and optionally a second table that describes named
arguments::

    // Arguments:
    //   v1 = The first vector.
    //   v2 = The second vector.
    //   ---
    //   fast = Use fast, but less comprehensive calculation method.
    //   dflt = Default value.

**Arguments:**

+----------------+--------------------------------------------------------+
| Positional Arg | What it Does                                           |
+================+========================================================+
| ``v1``         | The first vector.                                      |
+----------------+--------------------------------------------------------+
| ``v2``         | The second vector.                                     |
+----------------+--------------------------------------------------------+

+-------------+-----------------------------------------------------------+
| Named Arg   | What it Does                                              |
+=============+===========================================================+
| ``fast``    | If true, use fast, but less accurate calculation method.  |  
+-------------+-----------------------------------------------------------+
| ``dflt``    | Default value.                                            |
+-------------+-----------------------------------------------------------+


Figure Block
--------------

A Figure block generates and shows an image from a script in the multi-line
body, by running it in OpenSCAD.  A Figures block (plural) does the same, but
treats each line of the body as a separate Figure block::

    // Figure: Figure description
    //   cylinder(h=100, d1=75, d2=50);
    //   up(100) cylinder(h=100, d1=50, d2=75);
    // Figure(Spin,VPD=444): Animated figure that spins to show all faces.
    //   cube([10,100,50], center=true);
    //   cube([100,10,30], center=true);
    // Figures: This creates three separate images.
    //   cube(100);
    //   cylinder(h=100,d=50);
    //   sphere(d=100);

The metadata of the Figure block can contain various directives to alter how
the image will be generated.  These can be comma separated to give multiple
metadata directives:

- `NORENDER`: Don't generate an image for this example, but show the example text.
- `Hide`: Generate, but don't show script or image.  This can be used to generate images to be manually displayed in markdown text blocks.
- `2D`: Orient camera in a top-down view for showing 2D objects.
- `3D`: Orient camera in an oblique view for showing 3D objects.
- `VPD=440`: Force viewpoint distance `$vpd` to 440.
- `VPT=[10,20,30]` Force the viewpoint translation `$vpt` to `[10,20,30]`.
- `VPR=[55,0,600]` Force the viewpoint rotation `$vpr` to `[55,0,60]`.
- `Spin`: Animate camera orbit around the `[0,1,1]` axis to display all sides of an object.
- `FlatSpin`: Animate camera orbit around the Z axis, above the XY plane.
- `Anim`: Make an animation where `$t` varies from `0.0` to almost `1.0`.
- `Small`: Make the image small sized.
- `Med`: Make the image medium sized.
- `Big`: Make the image big sized.
- `Huge`: Make the image huge sized.
- `Size=880x640`: Make the image 880 by 640 pixels in size.
- `Render`: Force full rendering from OpenSCAD, instead of the normal preview.
- `Edges`: Highlight face edges.


Example Block
-------------

An Example block shows a script, and possibly generates an image from it.
The script is in the multi-line body.  The `Examples` (plural) block does
the same, but it treats eash body line as a separate Example bloc to show.
Any images, if generated, will be created by running it in OpenSCAD::

    // Example: Example description
    //   cylinder(h=100, d1=75, d2=50);
    //   up(100) cylinder(h=100, d1=50, d2=75);
    // Example(Spin,VPD=444): Animated shape that spins to show all faces.
    //   cube([10,100,50], center=true);
    //   cube([100,10,30], center=true);
    // Examples: This creates three separate Examples with images.
    //   cube(100);
    //   cylinder(h=100,d=50);
    //   sphere(d=100);

The metadata of the Example block can contain various directives to alter how
the image will be generated.  These can be comma separated to give multiple
metadata directives:

- `NORENDER`: Don't generate an image for this example, but show the example text.
- `Hide`: Generate, but don't show script or image.  This can be used to generate images to be manually displayed in markdown text blocks.
- `2D`: Orient camera in a top-down view for showing 2D objects.
- `3D`: Orient camera in an oblique view for showing 3D objects. Often used to force an Example sub-block to generate an image in Function and Constant blocks.
- `VPD=440`: Force viewpoint distance `$vpd` to 440.
- `VPT=[10,20,30]` Force the viewpoint translation `$vpt` to `[10,20,30]`.
- `VPR=[55,0,600]` Force the viewpoint rotation `$vpr` to `[55,0,60]`.
- `Spin`: Animate camera orbit around the `[0,1,1]` axis to display all sides of an object.
- `FlatSpin`: Animate camera orbit around the Z axis, above the XY plane.
- `Anim`: Make an animation where `$t` varies from `0.0` to almost `1.0`.
- `Small`: Make the image small sized.
- `Med`: Make the image medium sized.
- `Big`: Make the image big sized.
- `Huge`: Make the image huge sized.
- `Size=880x640`: Make the image 880 by 640 pixels in size.
- `Render`: Force full rendering from OpenSCAD, instead of the normal preview.
- `Edges`: Highlight face edges.

Modules will default to generating and displaying the image as if the ``3D``
directive is given.  Functions and constants will default to not generating
an image unless ``3D``, ``Spin``, ``FlatSpin`` or ``Anim`` is explicitly given.

If any lines of the Example script begin with ``--``, then they are not shown in
the example script output to the documentation, but they *are* included in the
script used to generate the example image, without the ``--``, of course::

    // Example: Multi-line example.
    //   --$fn = 72; // Lines starting with -- aren't shown in docs example text.
    //   lst = [
    //       "multi-line examples",
    //       "are shown in one block",
    //       "with a single image.",
    //   ];
    //   foo(lst, 23, "blah");


Creating Custom Block Headers
=============================

If you have need of a non-standard documentation block in your docs, you can
declare the new block type using ``DefineHeader:``.  This has the syntax::

    // DefineHeader(TYPE): NEWBLOCKNAME

Where NEWBLOCKNAME is the name of the new block header, and TYPE defines the
behavior of the new block.  TYPE can be one of:

- ``Generic``: Show both the TitleText and body.
- ``Text``: Show the TitleText as the first line of the body.
- ``Label``: Show only the TitleText and no body.
- ``NumList``: Shows TitleText, and the body lines in a numbered list.
- ``BulletListList``: Shows TitleText, and the body lines in a bullet list.
- ``Table``: Shows TitleText, and body lines in a definition table.
- ``Figure``: Shows TitleText, and an image rendered from the script in the Body.
- ``Example``: Like Figure, but also shows the body as an example script.


Generic Block Type
------------------

The Generic block header type takes both title and body lines and generates a
markdown block that has the block header, title, and a following body::

    // DefineHeader(Generic): Result
    // Result: For Typical Cases
    //   Does typical things.
    //   Or something like that.
    // Result: For Atypical Cases
    //   Performs an atypical thing.

**Result:** For Typical Cases

Does typical things.

Or something like that.

**Result:** For Atypical Cases

Performs an atypical thing.


Text Block Type
---------------

The Text block header type is similar to the Generic type, except it merges
the title into the body.  This is useful for allowing single-line or multi-
line blocks::

    // DefineHeader(Text): Reason
    // Reason: This is a simple reason.
    // Reason: This is a complex reason.
    //   It is a multi-line explanation
    //   about why this does what it does.

**Reason:**
This is a simple reason.

**Reason:**
This is a complex reason.
It is a multi-line explanation
about why this does what it does.


Label Block Type
----------------

The Label block header type takes just the title, and shows it with the header::

    // DefineHeader(Label): Regions
    // Regions: Antarctica, New Zealand
    // Regions: Europe, Australia

**Regions:** Antarctica, New Zealand
**Regions:** Europe, Australia


NumList Block Type
------------------

The NumList block header type takes both title and body lines, and outputs a
numbered list block::

    // DefineHeader(NumList): Steps
    // Steps: How to handle being on fire.
    //   Stop running around and panicing.
    //   Drop to the ground.
    //   Roll on the ground to smother the flames.

**Steps:** How to handle being on fire.
1. Stop running around and panicing.
2. Drop to the ground.
3. Roll on the ground to smother the flames.


BulletList Block Type
---------------------

The BulletList block header type takes both title and body lines::

    // DefineHeader(BulletList): Side Effects
    // Side Effects: For Typical Uses
    //   The variable `foo` gets set.
    //   The default for subsequent calls is updated.

**Side Effects:** For Typical Uses
- The variable $foo gets set.
- The default for subsequent calls is updated.


Table Block Type
------------------

The Table block header type outputs a header block with the title, followed by
one or more tables.  This is genertally meant for definition lists.  The header
names are given in the DefineHeader metadata.  Header names are separated by
``|`` (vertical bar, or pipe) characters, and sets of headers (for multiple
tables) are separated by ``||`` (two vertical bars).  A header that starts with
the ``^`` (hat, or circumflex) character, will cause the items in that column
to be surrounded by \`foo\` literal markers.  Cells in the body content are
separated by ``=`` (equals signs)::

    // DefineHeader(Table:^Link Name|Description): Anchors
    // Anchors: by Name
    //   "link1" = Anchor for the joiner Located at the back side of the shape.
    //   "a"/"b" = Anchor for the joiner Located at the front side of the shape.

**Anchors:** by Name

+--------------------+--------------------------------------------------------+
| Link Name          | Description                                            |
+====================+========================================================+
| ``"link1"``        | Anchor for the joiner at the back side of the shape.   |
+--------------------+--------------------------------------------------------+
| ``"a"`` / ``"b"``  | Anchor for the joiner at the front side of the shape.  |
+--------------------+--------------------------------------------------------+

You can have multiple subtables, separated by a line with only three dashes: ``---``::

    // DefineHeader(Table:^Pos Arg|What it Does||^Names Arg|What it Does): Args
    // Args:
    //   foo = The foo argument.
    //   bar = The bar argument.
    //   ---
    //   baz = The baz argument.
    //   qux = The baz argument.

**Args:**

+-------------+--------------------------------------------------------+
| Pos Arg     | What it Does                                           |
+=============+========================================================+
| ``foo``     | The foo argument.                                      |
+-------------+--------------------------------------------------------+
| ``bar``     | The bar argument.                                      |
+-------------+--------------------------------------------------------+

+-------------+--------------------------------------------------------+
| Named Arg   | What it Does                                           |
+=============+========================================================+
| ``baz``     | The baz argument.                                      |
+-------------+--------------------------------------------------------+
| ``qux``     | The qux argument.                                      |
+-------------+--------------------------------------------------------+


Defaults Configuration
======================

The ``openscad_decsgen`` script looks for an ``.openscad_docsgen_rc`` file in
the source code directory it is run in.  In that file, you can give a few
defaults for what files will be processed, and where to save the generated
markdown documentation.

To ignore specific files, to prevent generating documentation for them, you
can use the IgnoreFiles block.   Note that the commentline prefix is not
needed in the configuration file::

    IgnoreFiles:
      ignored1.scad
      ignored2.scad

To prioritize the ordering of files when generating the Table of Contents
and other indices, you can use the PrioritizeFiles block::

    PrioritizeFiles:
      file1.scad
      file2.scad

To specify what directory to write the markdown output documentation to, you
can use the DocsDirectory block::

    DocsDirectory: wiki_dir

You can also use the DefineHeader block in the config file to make custom
block headers::

    DefineHeader(Text): Returns
    DefineHeader(BulletList): Side Effects
    DefineHeader(Table:^Anchor Name|Position): Extra Anchors



