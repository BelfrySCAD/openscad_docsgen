import types
import pytest
from openscad_docsgen.blocks import (
    DocsGenException,
    GenericBlock,
    LabelBlock,
    FileBlock,
    SectionBlock,
    SubsectionBlock,
    ItemBlock,
    BulletListBlock,
    NumberedListBlock,
    TableBlock,
    TextBlock,
    DefinitionsBlock,
    IncludesBlock,
    HeaderlessBlock,
)
from openscad_docsgen.target_wiki import Target_Wiki


def make_origin(file="test.scad", line=1):
    return types.SimpleNamespace(file=file, line=line)


def make_controller():
    return types.SimpleNamespace(
        items_by_name={},
        definitions={},
        defn_aliases={},
    )


def make_target():
    return Target_Wiki(docs_dir="/tmp/docs")


# --- DocsGenException ---

def test_docs_gen_exception_contains_block():
    exc = DocsGenException("MyBlock", "Something went wrong")
    assert "MyBlock" in str(exc)


def test_docs_gen_exception_contains_message():
    exc = DocsGenException("MyBlock", "Something went wrong")
    assert "Something went wrong" in str(exc)


def test_docs_gen_exception_attributes():
    exc = DocsGenException("MyBlock", "bad")
    assert exc.block == "MyBlock"
    assert exc.message == "bad"


# --- GenericBlock ---

def test_generic_block_str():
    b = GenericBlock("Function", "myFunc()", [], make_origin())
    assert str(b) == "Function: myFunc()"


def test_generic_block_str_ampersand_replaced():
    b = GenericBlock("Function&Module", "foo()", [], make_origin())
    assert str(b) == "Function/Module: foo()"


def test_generic_block_parent_child_relationship():
    parent = GenericBlock("Parent", "p", [], make_origin())
    child = GenericBlock("Child", "c", [], make_origin(), parent=parent)
    assert child in parent.children
    assert child.parent is parent


def test_generic_block_no_parent():
    b = GenericBlock("Block", "sub", [], make_origin())
    assert b.parent is None
    assert b.children == []


def test_generic_block_eq():
    b1 = GenericBlock("Function", "foo()", [], make_origin())
    b2 = GenericBlock("Function", "foo()", [], make_origin())
    assert b1 == b2


def test_generic_block_not_eq():
    b1 = GenericBlock("Function", "foo()", [], make_origin())
    b2 = GenericBlock("Function", "bar()", [], make_origin())
    assert b1 != b2


def test_generic_block_lt_by_subtitle():
    b1 = GenericBlock("Function", "aaa()", [], make_origin())
    b2 = GenericBlock("Function", "bbb()", [], make_origin())
    assert b1 < b2


def test_generic_block_lt_by_title_when_subtitle_equal():
    b1 = GenericBlock("Alpha", "same", [], make_origin())
    b2 = GenericBlock("Beta", "same", [], make_origin())
    assert b1 < b2


def test_generic_block_get_children_by_title_string():
    parent = GenericBlock("Parent", "p", [], make_origin())
    c1 = GenericBlock("Usage", "u1", [], make_origin(), parent=parent)
    c2 = GenericBlock("Arguments", "a", [], make_origin(), parent=parent)
    c3 = GenericBlock("Usage", "u2", [], make_origin(), parent=parent)
    usages = parent.get_children_by_title("Usage")
    assert usages == [c1, c3]
    assert c2 not in usages


def test_generic_block_get_children_by_title_list():
    parent = GenericBlock("Parent", "p", [], make_origin())
    c1 = GenericBlock("Usage", "u", [], make_origin(), parent=parent)
    c2 = GenericBlock("Arguments", "a", [], make_origin(), parent=parent)
    result = parent.get_children_by_title(["Usage", "Arguments"])
    assert c1 in result
    assert c2 in result


def test_generic_block_get_markdown_body_plain():
    b = GenericBlock("Foo", "bar", ["line one", "line two"], make_origin())
    lines = b.get_markdown_body(make_controller(), make_target())
    assert "line one" in lines
    assert "line two" in lines


def test_generic_block_get_markdown_body_dot_blank():
    b = GenericBlock("Foo", "bar", [".", "text"], make_origin())
    lines = b.get_markdown_body(make_controller(), make_target())
    assert "" in lines
    assert "text" in lines


def test_generic_block_get_markdown_body_code_fence():
    b = GenericBlock("Foo", "bar", ["```", "code here", "```"], make_origin())
    lines = b.get_markdown_body(make_controller(), make_target())
    assert "code here" in lines


def test_generic_block_get_data():
    b = GenericBlock("Function", "foo()", ["body"], make_origin("test.scad", 5))
    d = b.get_data()
    assert d["name"] == "Function"
    assert d["subtitle"] == "foo()"
    assert d["body"] == ["body"]
    assert d["file"] == "test.scad"
    assert d["line"] == 5


# --- FileBlock ---

def test_file_block_uses_filename_as_default_display_title():
    block = FileBlock("LibFile", "mylib.scad", [], make_origin("mylib.scad"))
    assert block.display_title == "mylib.scad"


def test_file_block_uses_explicit_display_title():
    block = FileBlock("LibFile", "mylib.scad", [], make_origin("mylib.scad"))
    block.file_title = "Core Shapes"
    SectionBlock("Section", "Basics", [], make_origin("mylib.scad"), parent=block)
    assert block.display_title == "Core Shapes"
    assert block.get_data()["filetitle"] == "Core Shapes"


def test_file_block_heading_uses_explicit_display_title():
    block = FileBlock("LibFile", "mylib.scad", [], make_origin("mylib.scad"))
    block.file_title = "Core Shapes"
    lines = block.get_file_lines(make_controller(), make_target())
    assert lines[0] == "# Core Shapes"
    assert "mylib.scad" not in lines[0]


def test_file_block_heading_keeps_legacy_title_by_default():
    block = FileBlock("LibFile", "mylib.scad", [], make_origin("mylib.scad"))
    lines = block.get_file_lines(make_controller(), make_target())
    assert lines[0] == "# LibFile: mylib.scad"


def test_sort_children_back_blocks_last():
    parent = GenericBlock("Parent", "p", [], make_origin())
    c_example = GenericBlock("Example", "e", [], make_origin(), parent=parent)
    c_usage = GenericBlock("Usage", "u", [], make_origin(), parent=parent)
    c_desc = GenericBlock("Description", "d", [], make_origin(), parent=parent)

    front = [["Usage"], ["Description"]]
    back = [["Example"]]
    sorted_children = parent.sort_children(front, back)

    assert sorted_children.index(c_usage) < sorted_children.index(c_example)
    assert sorted_children.index(c_desc) < sorted_children.index(c_example)


# --- LabelBlock ---

def test_label_block_no_body():
    b = LabelBlock("Label", "subtitle", [], make_origin())
    assert b.title == "Label"
    assert b.subtitle == "subtitle"


def test_label_block_raises_with_body():
    with pytest.raises(DocsGenException):
        LabelBlock("Label", "subtitle", ["body line"], make_origin())


# --- FileBlock ---

def test_file_block_basic_attrs():
    b = FileBlock("LibFile", "mylib.scad", ["body"], make_origin())
    assert b.title == "LibFile"
    assert b.subtitle == "mylib.scad"
    assert b.includes == []
    assert b.common_code == []
    assert b.footnotes == []
    assert b.summary == ""


def test_file_block_get_figure_num():
    b = FileBlock("File", "test.scad", [], make_origin())
    assert b.get_figure_num() == "0"


def test_file_block_get_data_has_expected_keys():
    b = FileBlock("File", "test.scad", [], make_origin())
    # get_data() filters d["children"], which requires at least one child to exist
    SectionBlock("Section", "s", [], make_origin(), parent=b)
    d = b.get_data()
    assert "includes" in d
    assert "commoncode" in d
    assert "group" in d
    assert "summary" in d
    assert "footnotes" in d


# --- SectionBlock ---

def test_section_block_increments_parent_figure_num():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    assert file_block.figure_num == 0
    SectionBlock("Section", "My Section", [], make_origin(), parent=file_block)
    assert file_block.figure_num == 1


def test_section_block_multiple_increments():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    SectionBlock("Section", "S1", [], make_origin(), parent=file_block)
    SectionBlock("Section", "S2", [], make_origin(), parent=file_block)
    assert file_block.figure_num == 2


# --- SubsectionBlock ---

def test_subsection_increments_section_figure_num():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "S", [], make_origin(), parent=file_block)
    assert section.figure_num == 0
    SubsectionBlock("Subsection", "Sub1", [], make_origin(), parent=section)
    assert section.figure_num == 1


# --- ItemBlock ---

def test_item_block_str_simplifies_args():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "s", [], make_origin(), parent=file_block)
    item = ItemBlock("Function", "myFunc()", [], make_origin(), parent=section)
    assert str(item) == "Function: myFunc()"


def test_item_block_str_with_ampersand():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "s", [], make_origin(), parent=file_block)
    item = ItemBlock("Function&Module", "fm()", [], make_origin(), parent=section)
    assert str(item) == "Function/Module: fm()"


def test_item_block_raises_with_nonempty_parens():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "s", [], make_origin(), parent=file_block)
    with pytest.raises(DocsGenException):
        ItemBlock("Function", "myFunc(bad arg)", [], make_origin(), parent=section)


def test_item_block_empty_parens_ok():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "s", [], make_origin(), parent=file_block)
    item = ItemBlock("Function", "myFunc()", [], make_origin(), parent=section)
    assert item.title == "Function"
    assert item.subtitle == "myFunc()"


def test_item_block_initial_state():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "s", [], make_origin(), parent=file_block)
    item = ItemBlock("Module", "myMod()", [], make_origin(), parent=section)
    assert item.deprecated is False
    assert item.topics == []
    assert item.aliases == []
    assert item.see_also == []
    assert item.synopsis == ""


def test_item_block_get_funmod_function():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "s", [], make_origin(), parent=file_block)
    item = ItemBlock("Function", "f()", [], make_origin(), parent=section)
    assert item.get_funmod() == "Func"


def test_item_block_get_funmod_module():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "s", [], make_origin(), parent=file_block)
    item = ItemBlock("Module", "m()", [], make_origin(), parent=section)
    assert item.get_funmod() == "Mod"


def test_item_block_get_funmod_function_and_module():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "s", [], make_origin(), parent=file_block)
    item = ItemBlock("Function&Module", "fm()", [], make_origin(), parent=section)
    assert item.get_funmod() == "Func/Mod"


def test_item_block_get_funmod_constant():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    section = SectionBlock("Section", "s", [], make_origin(), parent=file_block)
    item = ItemBlock("Constant", "MY_CONST", [], make_origin(), parent=section)
    assert item.get_funmod() == "Const"


# --- BulletListBlock ---

def test_bullet_list_block_get_file_lines():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    b = BulletListBlock("Usage", "", ["foo(a)", "foo(b)"], make_origin(), parent=file_block)
    lines = b.get_file_lines(make_controller(), make_target())
    assert any("foo(a)" in l for l in lines)
    assert any("foo(b)" in l for l in lines)


# --- NumberedListBlock ---

def test_numbered_list_block_get_file_lines():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    b = NumberedListBlock("Steps", "", ["step 1", "step 2"], make_origin(), parent=file_block)
    lines = b.get_file_lines(make_controller(), make_target())
    assert any("step 1" in l for l in lines)
    assert any("step 2" in l for l in lines)


# --- TableBlock ---

def test_table_block_get_file_lines():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    headers = [["By Position", "What it does"]]
    b = TableBlock("Arguments", "", ["a = a parameter"], make_origin(), parent=file_block, header_sets=headers)
    lines = b.get_file_lines(make_controller(), make_target())
    assert any("a parameter" in l for l in lines)


def test_table_block_raises_more_tables_than_header_sets():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    headers = [["Name", "Value"]]
    with pytest.raises(DocsGenException):
        TableBlock("Args", "", ["a = 1", "---", "b = 2"], make_origin(), parent=file_block, header_sets=headers)


# --- TextBlock ---

def test_text_block_moves_subtitle_to_body():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    b = TextBlock("Description", "my subtitle text", [], make_origin(), parent=file_block)
    assert b.subtitle == ""
    assert "my subtitle text" in b.body


# --- HeaderlessBlock ---

def test_headerless_block_moves_subtitle_to_body():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    b = HeaderlessBlock("Continues", "continuation text", [], make_origin(), parent=file_block)
    assert b.subtitle == ""
    assert "continuation text" in b.body


# --- DefinitionsBlock ---

def test_definitions_block_parses_terms():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    b = DefinitionsBlock("Glossary", "", ["term1 = A definition"], make_origin(), parent=file_block)
    assert "term1" in b.definitions


def test_definitions_block_aliases_via_pipe():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    b = DefinitionsBlock("Glossary", "", ["term1|alias1 = A definition"], make_origin(), parent=file_block)
    assert "term1" in b.definitions


def test_definitions_block_raises_on_duplicate():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    with pytest.raises(DocsGenException):
        DefinitionsBlock("Glossary", "", ["term = Def1", "term = Def2"], make_origin(), parent=file_block)


def test_definitions_block_raises_no_equals():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    with pytest.raises(DocsGenException):
        DefinitionsBlock("Glossary", "", ["no equals sign here"], make_origin(), parent=file_block)


# --- IncludesBlock ---

def test_includes_block_adds_to_parent():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    IncludesBlock("Includes", "", ["include <foo.scad>", "include <bar.scad>"], make_origin(), parent=file_block)
    assert "include <foo.scad>" in file_block.includes
    assert "include <bar.scad>" in file_block.includes


def test_includes_block_empty_body():
    file_block = FileBlock("File", "test.scad", [], make_origin())
    IncludesBlock("Includes", "", [], make_origin(), parent=file_block)
    assert file_block.includes == []
