from __future__ import print_function

import re
import sys
import string
import os.path

from .imagemanager import ImageRequest, ImageManager


imgmgr = ImageManager()

def mkdn_esc(txt):
    out = ""
    quotpat = re.compile(r'([^`]*)(`[^`]*`)(.*$)')
    while txt:
        m = quotpat.match(txt)
        if m:
            out += m.group(1).replace(r'_', r'\_').replace(r'&',r'&amp;').replace(r'<', r'&lt;').replace(r'>',r'&gt;')
            out += m.group(2)
            txt = m.group(3)
        else:
            out += txt.replace(r'_', r'\_').replace(r'&',r'&amp;').replace(r'<', r'&lt;').replace(r'>',r'&gt;')
            txt = ""
    return out


def flatten(l, ltypes=(list, tuple)):
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)


def header_link(name):
    refpat = re.compile("[^a-z0-9_ -]")
    return refpat.sub("", name.lower()).replace(" ", "-")


def block_link(item, srcfile="", prefix=""):
    return "{}[{}]({}#{})".format(
        prefix,
        mkdn_esc(str(item)),
        srcfile,
        header_link(str(item))
    )


class DocsGenException(Exception):
    def __init__(self, block="", message=""):
        self.block = block
        self.message = message
        super().__init__("{} {}".format(self.message, self.block))


class GenericBlock(object):
    def __init__(self, title, subtitle, body, parent=None):
        self.title = title
        self.subtitle = sibtitle
        self.body = body
        self.parent = parent
        self.children = []
        self.figure_num = 0
        if parent:
            parent.add_node(parent)

    def __str__(self):
        return "{}: {}".format(
            mkdn_esc(self.title.replace('&', '/')),
            mkdn_esc(self.subtitle)
        )

    def add_child(self, child):
        self.children.append(child)

    def sort_children(self, front_blocks=(), back_blocks=()):
        children = []
        for blocks in front_blocks:
            for child in self.children:
                if child.title in blocks:
                    children.append(child)
        blocks = flatten(front_blocks + back_blocks)
        for child in self.children:
            if child.title not in blocks:
                children.append(child)
        for blocks in back_blocks:
            for child in self.children:
                if child.title in blocks:
                    children.append(child)
        return children

    def get_toc_lines(self):
        return []

    def get_markdown_body(self):
        out = []
        if not self.body:
            return out
        in_block = False
        for line in self.body:
            if line.startswith("```"):
                in_block = not in_block
            if in_block or line.startswith("    "):
                out.append(line)
            elif line == ".":
                out.append("")
            else:
                out.append(mkdn_esc(line))
        return out

    def get_markdown(self):
        out = []
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(self.subtitle)))
        out.extend(self.get_markdown_body())
        out.append("")
        return out

    def __eq__(self, other):
        return self.title == other.title and self.subtitle == other.subtitle

    def __lt__(self, other):
        if self.subtitle == other.subtitle:
            return self.title < other.title
        return self.subtitle < other.subtitle


class LabelBlock(GenericBlock):
    def __init__(self, title, subtitle, body, parent=None):
        if body:
            raise DocsGenException(title, "Body not supported, while declaring block:")
        super().__init__(title, subtitle, body, parent=parent)


class TextBlock(GenericBlock):
    def __init__(self, title, subtitle, body, parent=None):
        if subtitle:
            body.insert(0, subtitle)
            subtitle = ""
        super().__init__(title, subtitle, body, parent=parent)


class UnorderedListBlock(GenericBlock):
    def __init__(self, title, subtitle, body, parent=None):
        super().__init__(title, subtitle, body, parent=parent)

    def get_markdown(self):
        out = []
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(self.subtitle)))
        for line in self.body:
            out.append("- {}".format(mkdn_esc(line)))
        return out


class OrderedListBlock(GenericBlock):
    def __init__(self, title, subtitle, body, parent=None):
        super().__init__(title, subtitle, body, parent=parent)

    def get_markdown(self):
        out = []
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(self.subtitle)))
        for i, line in enumerate(self.body):
            out.append("{}. {}".format(i, mkdn_esc(line)))
        return out


class TableBlock(GenericBlock):
    def __init__(self, title, subtitle, body, parent=None, header_sets=None):
        super().__init__(title, subtitle, body, parent=parent)
        self.header_sets = header_sets

    def get_markdown(self):
        prev_tnum = -1
        tnum = 0
        table = []
        tables = []
        for line in self.body:
            if line == "---":
                tnum += 1
                if table:
                    tables.append(table)
                    table = []
                continue

            hdr_set = self.header_sets[tnum]
            cells = line.split("=",len(hdr_set))
            if len(cells) != len(hdr_set):
                raise DocsGenException(title, "More cells than table headers, while declaring block:")

            if prev_tnum != tnum:
                prev_tnum = tnum
                hcells = []
                lcells = []
                for hdr in hdr_set:
                    if hdr.startswith("^"):
                        hdr.rstrip("^")
                    hcells.append(mkdn_esc(hdr))
                    lcells.append("-"*min(20,len(hdr)))
                table.append(" | ".join(hcells))
                table.append(" | ".join(lcells))

            fcells = []
            for i in range(len(cells)):
                cell = cells[i]
                hdr = hdr_set[i]
                if hdr.startswith("^"):
                    cell = " / ".join("`{}`".format(x.strip()) for x in cell.split("/"))
                else:
                    cell = mkdn_esc(cell)
                fcells.append(cell)
            table.append( fcells )
        if table:
            tables.append(table)
        if tnum >= len(self.header_sets):
            raise DocsGenException(title, "More tables than header_sets, while declaring block:")
        out = []
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(self.subtitle)))
        tnum = 0
        for hdr_set, table in zip(self.header_sets, tables):
            out.append(' | '.join(hdr_set))
            out.append(' | '.join('-'*len(hdr) for hdr in hdr_set))
            for row in table:
                cells = ["{0:{width}s}".format(cell,width=min(20,len(hdr))) for hdr, cell in zip(hdr_set, row)]
                out.append(' | '.join(cells))
        out.append("")
        return out


class FileBlock(GenericBlock):
    def __init__(self, title, subtitle, body, src_file=None):
        super().__init__(title, subtitle, body)
        self.includes = []
        self.common_code = []
        self.src_file = src_file

    def get_toc_lines(self):
        out = []
        cnt = 0
        out.append("---")
        out.append("")
        out.append("# Table of Contents")
        out.append("")
        for child in self.children:
            if is_instance(child, SectionBlock):
                cnt += 1
                out.append(block_link(child, prefix="{}. ".format(cnt)))
                out.extend(child.get_toc_lines())
                out.append("")
        return out

    def get_markdown(self):
        out = []
        out.append("# {}".format(mkdn_esc(str(self))))
        out.extend(self.get_markdown_body())
        out.append("")
        for child in self.children:
            if not is_instance(child, SectionBlock):
                out.extend(child.get_markdown())
        out.extend(self.get_toc_lines())
        for child in self.children:
            if is_instance(child, SectionBlock):
                out.extend(child.get_markdown())
        return out


class IncludesBlock(GenericBlock):
    def __init__(self, title, subtitle, body, parent=None):
        super().__init__(title, subtitle, body, parent=parent)
        if parent:
            parent.includes.extent(body)

    def get_markdown(self):
        out = []
        if self.includes:
            out.append("To use, add the following lines to the beginning of your file:")
            out.append("")
            for line in self.includes:
                out.append("    " + line)
            out.append("")
        return out


class SectionBlock(GenericBlock):
    def __init__(self, title, subtitle, body, parent=None):
        super().__init__(title, subtitle, body, parent=parent)

    def get_toc_lines(self):
        out = []
        for child in self.children:
            if is_instance(child, ItemBlock):
                out.append(block_link(child, prefix="    - "))
        return out

    def get_markdown(self):
        out = []
        out.append("---")
        out.append("")
        out.append("## {}".format(mkdn_esc(str(self))))
        out.extend(self.get_markdown_body())
        out.append("")
        cnt = 0
        for child in self.children:
            chout = child.get_markdown()
            if chout:
                cnt += 1
            if cnt > 1:
                out.append("---")
                out.append("")
            out.extend(chout)
        return out


class ItemBlock(LabelBlock):
    _paren_pat = re.compile(r'\([^\)]+\)')

    def __init__(self, title, subtitle, body, parent=None):
        if self._paren_pat.search(subtitle):
            raise DocsGenException(title, "Text between parentheses, while declaring block:")
        super().__init__(title, subtitle, body, parent=parent)
        self.example_num = 0
        self.deprecated = False

    def __str__(self):
        return "{}: {}".format(
            self.title.replace('&', '/'),
            re.sub(r'\([^\)]*\)', r'()', self.subtitle)
        )

    def get_markdown(self):
        front_blocks = [
            ["Status"],
            ["Topics"],
            ["Usage"]
        ]
        back_blocks = [
            ["Example"]
        ]
        out = []
        out.append("### {}".format(mkdn_esc(str(self))))
        out.append("")
        for child in self.sort_children(front_blocks, back_blocks):
            out.extend(child.get_markdown())
        return out


class ImageBlock(GenericBlock):
    def __init__(self, title, subtitle, body, parent=None, meta="", image_root="", linenum=""):
        super().__init__(title, subtitle, body, parent=parent, meta=meta)
        self.meta = meta
        self.img_num = 0
        self.img_name = None
        self.img_root = self.img_root
        self.line_num = line_num
        if not "NORENDER" in meta:
            fileblock = self.parent
            while fileblock.parent:
                fileblock = fileblock.parent
            gentypes = ["File", "LibFile", "Module", "Function&Module"]
            if parent.title in gentypes or "3D" in meta or "2D" in meta or "Spin" in meta or "Anim" in meta:
                file_ext = "gif" if "Spin" in meta or "Anim" in meta else "png"
                if title == "Figure":
                    parent.figure_num += 1
                    self.img_num = parent.figure_num
                    self.img_name = "figure{}.{}".format(self.img_num, file_ext)
                else:
                    san_name = re.sub(r"[^A-Za-z0-9_]", "", parent.subtitle)
                    parent.example_num += 1
                    self.img_num = parent.example_num
                    img_suffix = ("_%d" % self.img_num) if self.img_num > 1 else "",
                    self.img_name = "{}{}.{}".format(san_name, img_suffix, file_ext)
                self.title = "{} {}".format(self.title, self.img_num)
                script_lines = []
                script_lines.extend(fileblock.includes)
                script_lines.extend(fileblock.common_code)
                for line in body:
                    if line.strip().startswith("--"):
                        script_lines.append(line.strip()[2:])
                    else:
                        script_lines.append(line)
                imgmgr.new_request(
                    fileblock.src_file, line_num,
                    self.img_root + self.img_name,
                    body, meta,
                    starting_cb=self._img_proc_start,
                    completion_cb=self._img_proc_done
                )

    def _img_proc_start(self, req):
        print("  " + os.path.basename(self.image_name))
        sys.stdout.flush()

    def _img_proc_done(self, req):
        if req.success:
            if req.status != "SKIP":
                print("    " + req.status)
                sys.stdout.flush()
            return
        out  = "\n".join(req.echos)
        out += "\n".join(req.warnings)
        out += "\n".join(req.errors)
        out += "//////////////////////////////////////////////////////////////////////"
        out += "// LibFile: {}  Line: {}  Image: {}".format(
            req.src_file, req.src_line, os.path.basename(req.image_file)
        )
        out += "//////////////////////////////////////////////////////////////////////"
        out += "\n".join(req.script_lines)
        out += "//////////////////////////////////////////////////////////////////////"
        print(out, file=sys.stderr)
        sys.exit(-1)

    def get_markdown(self):
        fileblock = self.parent
        while fileblock.parent:
            fileblock = fileblock.parent
        out = []
        if "Hide" in self.meta:
            return out
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(self.subtitle)))
        out.append("")
        if "Figure" not in self.title:
            out.extend(fileblock.includes)
            out.extend(["    " + line for line in self.body if not line.strip().startswith("--")])
            out.append("")
        if "NORENDER" not in self.meta:
            out.append(
                "![{0} Example{1}]({2}{3})".format(
                    mkdn_esc(self.parent.subtitle),
                    (" %d" % self.img_num) if self.parent.example_num > 1 else "",
                    self.imgroot,
                    self.image_name
                )
            )
        out.append("")


class FigureBlock(ImageBlock):
    def __init__(self, title, subtitle, body, parent=None, meta="", image_root="", linenum=""):
        super().__init__(title, subtitle, body, parent=None, meta=meta, image_root=image_root, linenum=linenum)


class ExampleBlock(ImageBlock):
    def __init__(self, title, subtitle, body, parent=None, meta="", image_root="", linenum=""):
        super().__init__(title, subtitle, body, parent=None, meta=meta, image_root=image_root, linenum=linenum)


class DocsGenParser(object):
    _header_pat = re.compile("^// ([A-Za-z0-9_& -]+)(\([^)]\))?: *(.*) *$")
    RCFILE = ".openscad_gendocs_rc"

    def __init__(self, docs_dir="docs"):
        self.docs_dir = docs_dir.rstrip("/")
        self.img_root = os.path.join(self.docs_dir, "images")
        self.file_blocks = []
        self.curr_file = None
        self.curr_section = None
        self.curr_item = None
        self.curr_parent = None
        self.ignored_files = []
        self.priority_files = []
        self.reset_header_defs()

    def reset_header_defs(self):
        self.header_defs = {
            # BlockHeader:   (parenttype, nodetype, extras, callback)
            'Status':        ( ItemBlock, LabelBlock, None, self._status_block_cb ),
            'Topics':        ( ItemBlock, LabelBlock, None, self._topics_block_cb ),
            'Arguments':     ( ItemBlock, TableBlock, (
                                     ('^<abbr title="These args can be used by position or by name.">By&nbsp;Position</abbr>', 'What it does'),
                                     ('^<abbr title="These args must be used by name, ie: name=value">By&nbsp;Name</abbr>', 'What it does')
                                 ), None
                             ),
        }
        lines = [
            "// DefineHeader(Text): Description",
            "// DefineHeader(BulletList): Usage",
        ]
        self.parse_lines(lines, src_file="Defaults")
        with open(self.RCFILE, "r") as f:
            lines = ["// " + line for line in f.readlines()]
            self.parse_lines(lines, src_file=self.RCFILE)

    def _status_block_cb(self, title, subtitle, body, meta):
        self.curr_item.deprecated = "DEPRECATED" in subtitle

    def _topics_block_cb(self, title, subtitle, body, meta):
        self.curr_item.topics = [x.strip() for x in subtitle.split(",")]

    def _skip_lines(self, lines, linenum=0):
        while linenum < len(lines):
            line = lines[linenum]
            match = self._header_pat.match(line)
            if match:
                return linenum
            linenum += 1
        return None

    def _files_prioritized(self):
        out = []
        found = {}
        for prifile in self.priority_files:
            for file_block in self.file_blocks:
                if file_block.subtitle == prifile:
                    found[pri_file] = True
                    out.append(file_block)
        for file_block in self.file_blocks:
            if file_block.subtitle not in found:
                out.append(file_block)
        return out

    def _define_blocktype(self, title, meta):
        title = title.strip()
        parentspec = None
        if "FuncBlock" in meta:
            parentspec = ItemBlock

        if "NumList" in meta:
            self.header_defs[title] = (parentspec, OrderedListBlock, None, None)
        elif "BulletList" in meta:
            self.header_defs[title] = (parentspec, UnorderedListBlock, None, None)
        elif "Table:" in meta:
            hdr_meta = mets.split("Table:",1)[1].split("||")
            hdr_sets = [[x.strip() for x in hset.split("|")] for hset in hdr_meta]
            self.header_defs[title] = (parentspec, TableBlock, hdr_sets, None)
        elif "Example" in meta:
            self.header_defs[title] = (parentspec, ExampleBlock, None, None)
        elif "Figure" in meta:
            self.header_defs[title] = (parentspec, FigureBlock, None, None)
        elif "Label" in meta:
            self.header_defs[title] = (parentspec, LabelBlock, None, None)
        elif "Text" in meta:
            self.header_defs[title] = (parentspec, TextBlock, None, None)
        elif "Generic" in meta:
            self.header_defs[title] = (parentspec, GenericBlock, None, None)
        else:
            raise DocsGenException("DefineHeader", "Could not parse target block type, while declaring block:")

    def _parse_block(self, lines, linenum=0, src_file=None):
        linenum = self._skip_lines(lines, linenum)
        hdr_linenum = linenum
        line = lines[linenum]
        match = self._header_pat.match(line)
        title = match.group(1)
        meta = match.group(2)
        subtitle = match.group(3)
        body = []
        linenum += 1

        while linenum < len(lines):
            line = lines[linenum]
            if not line.startswith("//   "):
                break
            body.append(line[5:].rstrip())
            linenum += 1

        try:
            parent = self.curr_parent
            if title == "DefineHeader":
                self._define_blocktype(subtitle, meta)
            elif title == "IgnoreFiles":
                if src_file != self.RCFILE:
                    raise DocsGenException(title, "Block disallowed outside of {} file:".format(self.RCFILE))
                if subtitle:
                    body.insert(0,subtitle)
                self.ignored_files.extend([
                    fname.strip() for fname in body
                ])
            elif title == "PrioritizeFiles":
                if src_file != self.RCFILE:
                    raise DocsGenException(title, "Block disallowed outside of {} file:".format(self.RCFILE))
                if subtitle:
                    body.insert(0,subtitle)
                self.priority_files = [x.strip() for x in body]
            elif title == "DocsDirectory":
                if src_file != self.RCFILE:
                    raise DocsGenException(title, "Block disallowed outside of {} file:".format(self.RCFILE))
                if bady:
                    raise DocsGenException(title, "Body not supported, while declaring block:")
                self.docs_dir = subtitle.strip().rstrip("/")
                self.img_root = os.path.join(self.docs_dir, "images")
            elif title in ["File", "LibFile"]:
                if self.curr_file:
                    raise DocsGenException(title, "File/Libfile block already specified, while declaring block:")
                self.curr_file = FileBlock(title, subtitle, body, src_file=src_file)
                self.curr_parent = self.curr_file
                self.file_blocks.append(self.curr_file)
            elif not self.curr_file:
                raise DocsGenException(title, "Must declare File or LibFile block before declaring block:")

            elif title == "Section":
                self.curr_section = SectionBlock(title, subtitle, body, parent=self.curr_file)
                self.curr_parent = self.curr_section
            elif title == "Includes":
                IncludesBlock(title, subtitle, body, parent=self.curr_file)
            elif title == "CommonCode":
                self.curr_file.common_code.extend(body)
            elif title == "Figure":
                FigureBlock(title, subtitle, body, parent=parent, meta=meta, image_root=self.img_root, linenum=hdr_linenum)
            elif title == "Example":
                ExampleBlock(title, subtitle, body, parent=parent, meta=meta, image_root=self.img_root, linenum=hdr_linenum)
            elif title == "Figures":
                for lnum, line in enumerate(body):
                    FigureBlock(title[:-1], subtitle, [line], parent=parent, meta=meta, image_root=self.img_root, linenum=hdr_linenum+lnum+1)
            elif title == "Examples":
                for lnum, line in enumerate(body):
                    ExampleBlock(title[:-1], subtitle, [line], parent=parent, meta=meta, image_root=self.img_root, linenum=hdr_linenum+lnum+1)
            elif title in self.header_defs:
                parcls, cls, data, cb = self.header_defs[title]
                if parcls and not is_instance(self.curr_parent, parcls):
                    raise DocsGenException(title, "Must be in Function/Module/Constant while declaring block:")
                if is_instance(cls, (GenericBlock, LabelBlock, TextBlock, OrderedListBlock, UnorderedListBlock)):
                    cls(title, subtitle, body, parent=parent)
                elif is_instance(cls, (TableBlock,)):
                    cls(title, subtitle, body, parent=parent, header_sets=data)
                elif is_instance(cls, (FigureBlock, ExampleBlock)):
                    cls(title, subtitle, body, parent=parent, meta=meta, image_root=self.img_root, linenum=hdr_linenum)
                cb(title, subtitle, body, meta)

            elif title in ["Constant", "Function", "Module", "Function&Module"]:
                if not self.curr_section:
                    raise DocsGenException(title, "Must declare Section before declaring block:")
                self.curr_item = ItemBlock(title, subtitle, body, parent=self.curr_section)
                self.curr_parent = self.curr_item
            else:
                raise DocsGenException(title, "Unrecognized block:")

            if linenum < len(lines) and not lines[linenum].startswith("//"):
                self.curr_item = None
            linenum = self._skip_lines(lines, linenum)

        except DocsGenException as e:
            print("{} at {}:{}".format(str(e), src_file, hdr_linenum), file=sys.stderr)
            sys.exit(-1)

        return linenum

    def parse_lines(self, lines, linenum=0, src_file=None):
        while linenum < len(lines):
            linenum = self._parse_block(lines, linenum, src_file=src_file)

    def parse_file(self, filename, commentless=False, images=True, test_only=False):
        if filename in self.ignored_files:
            return
        print("{}:".format(filename))
        self.src_file = filename
        self.curr_file = None
        self.curr_section = None
        self.reset_header_defs()
        with open(filename, "r") as f:
            if commentless:
                lines = ["// " + line for line in f.readlines()]
            else:
                lines = f.readlines()
            self.parse_lines(lines, src_file=filename)
        if images:
            imgmgr.process_requests(self.imgroot, test_only=test_only)

    def write_markdown_docsfiles(self):
        for fblock in self.file_blocks:
            filename = fblock.subtitle
            outfile = os.path.join(self.docs_dir, filename+".md")
            print("Writing {}...".format(outfile))
            with open(outfile,"w") as f:
                f.writelines(fblock.get_markdown())

    def write_toc_file(self):
        out = []
        out.append("# Table of Contents")
        out.append("")
        pri_blocks = self._files_prioritized()
        for fblock in pri_blocks:
            out.append("## {}".format(mkdn_esc(str(fblock))))
            filename = fblock.subtitle
            for sect in fblock.children:
                if is_instance(sect,SectionBlock):
                    out.append(block_link(sect, srcfile=filename, prefix="    -"))
                    for item in sect.children:
                        if is_instance(item,ItemBlock):
                            out.append(block_link(item, srcfile=filename, prefix="        -"))
        outfile = os.path.join(self.docs_dir, "TOC.md")
        print("Writing {}...".format(outfile))
        with open(outfile, "w") as f:
            f.writelines(out)

    def write_index_file(self):
        items = []
        for file_block in self.file_blocks:
            for section in file_block.children:
                if is_instance(section,SectionBlock):
                    for item in section.children:
                        if is_instance(item,ItemBlock):
                            items.append( (item, file_block) )
        sorted_items = sorted(items)
        out = []
        letters_found = []
        out.append("# Alphabetical Index of Functions, Modules, and Constants")
        out.append("")
        out.append("")
        for letter in string.ascii_uppercase:
            ltr_items = [
                item for item in sorted_items
                if item.subtitle.strip() and item.subtitle.strip().upper()[0] == letter
            ]
            if ltr_items:
                out.append("---")
                out.append("## {}".format(letter))
                letters_found.append(letter)
            for item in ltr_items:
                out.append(block_link(item, srcfile=filename, prefix="    -"))
        digit_items = [
            item for item in sorted_items
            if item.subtitle.strip() and item.subtitle.strip()[0].isdigit()
        ]
        if digit_items:
            out.append("---")
            out.append("## 0")
            letters_found.append('0')
        for item in digit_items:
            out.append(block_link(item, srcfile=filename, prefix="    -"))
        out.insert(2, ["[[{}]]".format(ltr) for ltr in letters_found])
        out.append("")
        outfile = os.path.join(self.docs_dir, "Index.md")
        print("Writing {}...".format(outfile))
        with open(outfile, "w") as f:
            f.writelines(out)

    def write_cheatsheet_file(self):
        out = []
        out.append("# The BOSL2 Cheat Sheet")
        out.append("")
        pri_blocks = self._files_prioritized()
        for file_block in pri_blocks:
            out.append("---")
            out.append("## {}".format(file_block))
            for section in file_block.children:
                if is_instance(section,SectionBlock):
                    out.append("### {}".format(section))
                    for item in section.children:
                        if is_instance(item,ItemBlock):
                            for usage in section.children:
                                if usage.title == "Usage":
                                    out.extend(usage.body)
            out.append("")
        outfile = os.path.join(self.docs_dir, "CheatSheet.md")
        print("Writing {}...".format(outfile))
        with open(outfile, "w") as f:
            f.writelines(out)
        return out


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
