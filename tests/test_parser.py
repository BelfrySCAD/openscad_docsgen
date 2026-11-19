import types
import pytest
from openscad_docsgen.parser import DocsGenParser
from openscad_docsgen.target_wiki import Target_Wiki


# --- Header pattern ---

_header_pat = DocsGenParser._header_pat


def test_header_pat_function():
    m = _header_pat.match("// Function: myFunc()")
    assert m is not None
    assert m.group(1) == "Function"
    assert m.group(4).strip() == "myFunc()"


def test_header_pat_libfile():
    m = _header_pat.match("// LibFile: mylib.scad")
    assert m is not None
    assert m.group(1) == "LibFile"
    assert m.group(4).strip() == "mylib.scad"


def test_header_pat_module():
    m = _header_pat.match("// Module: myMod()")
    assert m is not None
    assert m.group(1) == "Module"


def test_header_pat_function_and_module():
    m = _header_pat.match("// Function&Module: foo()")
    assert m is not None
    assert m.group(1) == "Function&Module"


def test_header_pat_with_meta():
    m = _header_pat.match("// Example(NORENDER): title")
    assert m is not None
    assert m.group(1) == "Example"
    assert m.group(3) == "(NORENDER)"
    assert m.group(4).strip() == "title"


def test_header_pat_with_multi_meta():
    m = _header_pat.match("// Example(3D;VPD=440): spin demo")
    assert m is not None
    assert "(3D;VPD=440)" in m.group(3)


def test_header_pat_no_subtitle():
    m = _header_pat.match("// Arguments:")
    assert m is not None
    assert m.group(1) == "Arguments"
    assert not m.group(4)


def test_header_pat_section():
    m = _header_pat.match("// Section: My Shapes")
    assert m is not None
    assert m.group(1) == "Section"
    assert m.group(4).strip() == "My Shapes"


def test_header_pat_define_header():
    m = _header_pat.match("// DefineHeader(BulletList;ItemOnly): Usage")
    assert m is not None
    assert m.group(1) == "DefineHeader"
    assert "BulletList" in m.group(3)


def test_header_pat_no_match_lowercase_header():
    assert _header_pat.match("// function: foo") is None


def test_header_pat_no_match_plain_comment():
    assert _header_pat.match("// this is just a comment") is None


def test_header_pat_no_match_code():
    assert _header_pat.match("sphere(10);") is None


def test_header_pat_no_match_empty_comment():
    assert _header_pat.match("//") is None


def test_header_pat_constant():
    m = _header_pat.match("// Constant: MY_CONST")
    assert m is not None
    assert m.group(1) == "Constant"


# --- Parser setup helper ---

def make_parser(tmp_path):
    target = Target_Wiki(docs_dir=str(tmp_path))
    opts = types.SimpleNamespace(
        target=target,
        strict=False,
        quiet=True,
        gen_toc=True,
        gen_index=False,
        gen_topics=False,
        gen_glossary=False,
        gen_cheat=False,
        sidebar_header=[],
        sidebar_middle=[],
        sidebar_footer=[],
    )
    return DocsGenParser(opts)


# --- _parse_meta_dict ---

def test_parse_meta_dict_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    d = parser._parse_meta_dict("Spin;3D")
    assert d["Spin"] == 1
    assert d["3D"] == 1


def test_parse_meta_dict_key_value(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    d = parser._parse_meta_dict("VPD=440;Size=800x600")
    assert d["VPD"] == "440"
    assert d["Size"] == "800x600"


def test_parse_meta_dict_mixed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    d = parser._parse_meta_dict("3D;VPD=440;Spin")
    assert d["3D"] == 1
    assert d["VPD"] == "440"
    assert d["Spin"] == 1


# --- Integration: parse LibFile block ---

LIBFILE_SCAD = """\
// LibFile: test.scad
//   A test library.
"""


def test_parse_libfile_creates_file_block(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(LIBFILE_SCAD.splitlines(), src_file="test.scad")
    assert len(parser.file_blocks) == 1
    assert parser.file_blocks[0].subtitle == "test.scad"


# --- Integration: parse FileTitle block ---

FILE_TITLE_SCAD = """\
// LibFile: test.scad
// FileTitle: Core Shapes
"""


def test_parse_file_title_sets_display_title(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(FILE_TITLE_SCAD.splitlines(), src_file="test.scad")
    assert parser.file_blocks[0].file_title == "Core Shapes"
    assert parser.file_blocks[0].display_title == "Core Shapes"


def test_file_title_is_used_in_toc_and_sidebar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(FILE_TITLE_SCAD.splitlines(), src_file="test.scad")

    parser.write_toc_file()
    parser.write_sidebar_file()

    toc = (tmp_path / "TOC.md").read_text()
    sidebar = (tmp_path / "_Sidebar.md").read_text()
    assert "[Core Shapes](#1-core-shapes)" in toc
    assert "## 1. [Core Shapes](test.scad)" in toc
    assert "[Core Shapes](test.scad)" in sidebar
    assert "[test.scad]" not in toc
    assert "[test.scad]" not in sidebar


# --- Integration: parse Section ---

SECTION_SCAD = """\
// LibFile: test.scad
// Section: Basic Shapes
"""


def test_parse_section_block(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(SECTION_SCAD.splitlines(), src_file="test.scad")
    file_block = parser.file_blocks[0]
    sections = file_block.get_children_by_title("Section")
    assert len(sections) == 1
    assert sections[0].subtitle == "Basic Shapes"


# --- Integration: parse Function ---

FUNCTION_SCAD = """\
// LibFile: test.scad
// Section: Funcs
// Function: myFunc()
"""


def test_parse_function_registers_in_items_by_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(FUNCTION_SCAD.splitlines(), src_file="test.scad")
    assert "myFunc()" in parser.items_by_name


def test_parse_function_item_type(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(FUNCTION_SCAD.splitlines(), src_file="test.scad")
    item = parser.items_by_name["myFunc()"]
    assert item.title == "Function"


# --- Integration: parse Module ---

MODULE_SCAD = """\
// LibFile: test.scad
// Section: Mods
// Module: myMod()
"""


def test_parse_module_registers_in_items_by_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(MODULE_SCAD.splitlines(), src_file="test.scad")
    assert "myMod()" in parser.items_by_name


# --- Integration: parse Aliases ---

ALIAS_SCAD = """\
// LibFile: test.scad
// Section: Funcs
// Function: myFunc()
// Aliases: myAlias()
"""


def test_parse_alias_registers_alias(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(ALIAS_SCAD.splitlines(), src_file="test.scad")
    assert "myAlias()" in parser.items_by_name


def test_parse_alias_points_to_same_item(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(ALIAS_SCAD.splitlines(), src_file="test.scad")
    assert parser.items_by_name["myAlias()"] is parser.items_by_name["myFunc()"]


def test_parse_alias_stored_on_item(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(ALIAS_SCAD.splitlines(), src_file="test.scad")
    item = parser.items_by_name["myFunc()"]
    assert "myAlias()" in item.aliases


# --- Integration: parse Constant ---

CONSTANT_SCAD = """\
// LibFile: test.scad
// Section: Constants
// Constant: MY_CONST
"""


def test_parse_constant_registers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(CONSTANT_SCAD.splitlines(), src_file="test.scad")
    assert "MY_CONST" in parser.items_by_name
    assert parser.items_by_name["MY_CONST"].title == "Constant"


# --- Integration: multiple sections in one file ---

MULTI_SECTION_SCAD = """\
// LibFile: test.scad
// Section: Section A
// Function: funcA()
// Section: Section B
// Function: funcB()
"""


def test_parse_multiple_sections(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(MULTI_SECTION_SCAD.splitlines(), src_file="test.scad")
    assert "funcA()" in parser.items_by_name
    assert "funcB()" in parser.items_by_name


# --- Integration: implicit section when no Section declared ---

NO_SECTION_SCAD = """\
// LibFile: test.scad
// Function: topLevel()
"""


def test_parse_function_without_section_creates_implicit_section(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = make_parser(tmp_path)
    parser.parse_lines(NO_SECTION_SCAD.splitlines(), src_file="test.scad")
    assert "topLevel()" in parser.items_by_name


# --- Integration: strict mode logs error without LibFile ---

def test_strict_mode_logs_error_without_file_block(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    from openscad_docsgen.errorlog import errorlog
    target = Target_Wiki(docs_dir=str(tmp_path))
    opts = types.SimpleNamespace(target=target, strict=True, quiet=True)
    parser = DocsGenParser(opts)
    initial_count = len(errorlog.errlist)
    parser.parse_lines(["// Section: Orphan Section"], src_file="test.scad")
    assert len(errorlog.errlist) > initial_count


# --- Integration: redeclaring a function logs an error ---

REDECLARE_SCAD = """\
// LibFile: test.scad
// Section: Funcs
// Function: myFunc()
// Function: myFunc()
"""


def test_parse_redeclared_function_logs_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    from openscad_docsgen.errorlog import errorlog
    parser = make_parser(tmp_path)
    initial_count = len(errorlog.errlist)
    parser.parse_lines(REDECLARE_SCAD.splitlines(), src_file="test.scad")
    assert len(errorlog.errlist) > initial_count
