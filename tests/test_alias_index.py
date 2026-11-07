"""BOSL2#2033: an alias was listed in AlphaIndex and Topics under the main
name, so the main name appeared twice and the alias not at all."""
import types

from openscad_docsgen.parser import DocsGenParser
from openscad_docsgen.target_githubwiki import Target_GitHubWiki

SRC = """\
// LibFile: u.scad
//   Utilities.

// Section: Types

// Function: is_int()
// Alias: is_integer()
// Topics: Type Checking
// Synopsis: Returns true if the argument is an integer.
// Usage:
//   bool = is_int(n);
// Description:
//   True for an integer.
function is_int(n) = is_num(n) && n == round(n);
"""


def test_an_alias_is_indexed_under_its_own_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "u.scad").write_text(SRC)
    docs = tmp_path / "docs"
    opts = types.SimpleNamespace(target=Target_GitHubWiki(docs_dir=str(docs)), strict=False, quiet=True)
    parser = DocsGenParser(opts)
    parser.parse_file("u.scad")
    parser.write_index_file()
    parser.write_topics_file()
    for name in ("AlphaIndex.md", "Topics.md"):
        text = (docs / name).read_text()
        assert text.count("[`is_int()`]") == 1, name
        assert text.count("[`is_integer()`](u.scad#function-is_int)") == 1, name
