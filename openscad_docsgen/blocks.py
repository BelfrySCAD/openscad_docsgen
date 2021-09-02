from __future__ import print_function

import os
import os.path
import re
import sys
import glob
import json
import string
import hashlib
from collections import namedtuple

from .imagemanager import ImageRequest, ImageManager


imgmgr = ImageManager()

def mkdn_esc(txt):
    out = ""
    quotpat = re.compile(r'([^`]*)(`[^`]*`)(.*$)')
    while txt:
        m = quotpat.match(txt)
        unquot  = m.group(1) if m else txt
        literal = m.group(2) if m else ""
        txt     = m.group(3) if m else ""
        unquot = unquot.replace(r'_', r'\_')
        unquot = unquot.replace(r'&',r'&amp;')
        unquot = unquot.replace(r'<', r'&lt;')
        unquot = unquot.replace(r'>',r'&gt;')
        out += unquot + literal
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


OriginInfo = namedtuple('OriginInfo', 'file line')


class DocsGenException(Exception):
    def __init__(self, block="", message=""):
        self.block = block
        self.message = message
        super().__init__('{} "{}"'.format(self.message, self.block))


class GenericBlock(object):
    _link_pat = re.compile(r'^(.*)\{\{([A-Za-z0-9_()]+)\}\}(.*)$')

    def __init__(self, title, subtitle, body, origin, parent=None):
        self.title = title
        self.subtitle = subtitle
        self.body = body
        self.origin = origin
        self.parent = parent
        self.children = []
        self.figure_num = 0
        if parent:
            parent.children.append(self)

    def __str__(self):
        return "{}: {}".format(
            self.title.replace('&', '/'),
            self.subtitle
        )

    def sort_children(self, front_blocks=(), back_blocks=()):
        children = []
        for child in self.children:
            found = [block for blocks in front_blocks for block in blocks if block in child.title]
            if found:
                children.append(child)
        blocks = flatten(front_blocks + back_blocks)
        for child in self.children:
            found = [block for block in blocks if block in child.title]
            if not found:
                children.append(child)
        for child in self.children:
            found = [block for blocks in back_blocks for block in blocks if block in child.title]
            if found:
                children.append(child)
        return children

    def get_children_by_title(self, title):
        return [
            child
            for child in self.children
            if child.title == title
        ]

    def get_data(self):
        d = {
            "name": self.title,
            "subtitle": self.subtitle,
            "body": self.body,
            "file": self.origin.file,
            "line": self.origin.line
        }
        if self.children:
            d["children"] = [child.get_data() for child in self.children]
        return d

    def get_link(self, label=None, currfile="", literalize=True):
        label = label if label is not None else self.subtitle
        if literalize:
            label = "`{0}`".format(label)
        else:
            label = mkdn_esc(label)
        return "[{0}]({1}#{2})".format(
            label,
            self.origin.file if self.origin.file != currfile else "",
            header_link(str(self))
        )

    def get_toc_lines(self, indent=4):
        return []

    def parse_links(self, line, controller):
        oline = ""
        while line:
            m = self._link_pat.match(line)
            if m:
                oline += mkdn_esc(m.group(1))
                name = m.group(2)
                line = m.group(3)
                if name not in controller.items_by_name:
                    msg = "Invalid Link {{{{{0}}}}}".format(name)
                    errorlog.add_entry(self.origin.file, self.origin.line, msg, ErrorLog.FAIL)
                    oline += mkdn_esc(name)
                else:
                    item = controller.items_by_name[name]
                    oline += item.get_link(label=name, currfile=self.origin.file)
            else:
                oline += mkdn_esc(line)
                line = ""
        return oline

    def get_markdown_body(self, controller):
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
                out.append(self.parse_links(line, controller))
        return out

    def get_markdown(self, controller):
        out = []
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(self.subtitle)))
        out.extend(self.get_markdown_body(controller))
        out.append("")
        return out

    def __eq__(self, other):
        return self.title == other.title and self.subtitle == other.subtitle

    def __lt__(self, other):
        if self.subtitle == other.subtitle:
            return self.title < other.title
        return self.subtitle < other.subtitle


class LabelBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        if body:
            raise DocsGenException(title, "Body not supported, while declaring block:")
        super().__init__(title, subtitle, body, origin, parent=parent)


class TopicsBlock(LabelBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)
        self.topics = [x.strip() for x in subtitle.split(",")]
        parent.topics = self.topics

    def get_markdown(self, controller):
        links = ", ".join("[{0}](Topics#{1})".format(mkdn_esc(topic),header_link(topic)) for topic in self.topics)
        out = []
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(links)))
        out.append("")
        return out


class SeeAlsoBlock(LabelBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)

    def get_markdown(self, controller):
        names = [name.strip() for name in self.subtitle.split(",")]
        items = []
        for name in names:
            if name not in controller.items_by_name:
                msg = "Invalid Link '{0}'".format(name)
                errorlog.add_entry(self.origin.file, self.origin.line, msg, ErrorLog.FAIL)
            else:
                item = controller.items_by_name[name]
                if item is not self.parent:
                    items.append( item )
        links = ", ".join( item.get_link(currfile=self.origin.file) for item in items )
        out = []
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(links)))
        out.append("")
        return out


class TextBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        if subtitle:
            body.insert(0, subtitle)
            subtitle = ""
        super().__init__(title, subtitle, body, origin, parent=parent)


class BulletListBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)

    def get_markdown(self, controller):
        out = []
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(self.subtitle)))
        out.append("")
        for line in self.body:
            out.append("- {}".format(self.parse_links(line, controller)))
        out.append("")
        return out


class NumberedListBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)

    def get_markdown(self, controller):
        out = []
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(self.subtitle)))
        out.append("")
        for i, line in enumerate(self.body):
            out.append("{}. {}".format(i+1, self.parse_links(line, controller)))
        out.append("")
        return out


class TableBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None, header_sets=None):
        super().__init__(title, subtitle, body, origin, parent=parent)
        self.header_sets = header_sets
        tnum = 0
        for line in self.body:
            if line == "---":
                tnum += 1
                continue
        if tnum >= len(self.header_sets):
            raise DocsGenException(title, "More tables than header_sets, while declaring block:")

    def get_markdown(self, controller):
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
            cells = [x.strip() for x in line.split("=",len(hdr_set)-1)]

            if prev_tnum != tnum:
                prev_tnum = tnum
                hcells = []
                lcells = []
                for hdr in hdr_set:
                    if hdr.startswith("^"):
                        hdr = hdr.lstrip("^")
                    hcells.append(hdr)
                    lcells.append("-"*min(20,len(hdr)))
                table.append(" | ".join(hcells))
                table.append(" | ".join(lcells))

            fcells = []
            for i in range(len(cells)):
                cell = cells[i]
                hdr = hdr_set[i]
                if hdr.startswith("^"):
                    cell = " / ".join("{:20s}".format("`{}`".format(x.strip())) for x in cell.split("/"))
                else:
                    cell = self.parse_links(cell,controller)
                fcells.append(cell)
            table.append( " | ".join(fcells) )
        if table:
            tables.append(table)
        out = []
        out.append(mkdn_esc("**{}:** {}".format(self.title, self.subtitle)))
        out.append("")
        for table in tables:
            out.extend(table)
            out.append("")
        return out


class FileBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin):
        super().__init__(title, subtitle, body, origin)
        self.includes = []
        self.common_code = []

    def get_data(self):
        d = super().get_data()
        d["includes"] = self.includes
        d["commoncode"] = self.common_code
        skip_titles = ["CommonCode", "Includes"]
        d["children"] = list(filter(lambda x: x["name"] not in skip_titles, d["children"]))
        return d

    def get_link(self, label=None, currfile="", literalize=False):
        label = label if label is not None else self.subtitle
        if literalize:
            label = "`{0}`".format(label)
        else:
            label = mkdn_esc(label)
        return "[{0}]({1})".format(label, self.origin.file)

    def get_toc_lines(self, indent=4):
        sections = [
            sect for sect in self.children
            if isinstance(sect, SectionBlock)
        ]
        out = []
        out.append("---")
        out.append("")
        out.append("# Table of Contents")
        out.append("")
        for n, sect in enumerate(sections):
            if sect.subtitle:
                out.append("{0}. {1}".format(
                    n+1, sect.get_link(
                        label=str(sect),
                        currfile=self.origin.file,
                        literalize=False
                    )
                ))
                out.extend(sect.get_toc_lines(indent=4))
            else:
                out.extend(sect.get_toc_lines(indent=0))
            out.append("")
        return out

    def get_markdown(self, controller):
        out = []
        out.append("# {}".format(mkdn_esc(str(self))))
        out.extend(self.get_markdown_body(controller))
        out.append("")
        for child in self.children:
            if not isinstance(child, SectionBlock):
                out.extend(child.get_markdown(controller))
        out.extend(self.get_toc_lines())
        for child in self.children:
            if isinstance(child, SectionBlock):
                out.extend(child.get_markdown(controller))
        return out


class IncludesBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)
        if parent:
            parent.includes.extend(body)

    def get_markdown(self, controller):
        out = []
        if self.body:
            out.append("To use, add the following lines to the beginning of your file:")
            out.append("")
            for line in self.body:
                out.append("    " + line)
            out.append("")
        return out


class SectionBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)

    def get_toc_lines(self, indent=4):
        """
        Return the markdown table of contents lines for the children in this
        section. This is returned as a series of bullet points.
        `indent` sets the level of indentation for the bullet points
        """
        out = []
        for child in self.children:
            if isinstance(child, ItemBlock):
                child_link = "- {}".format(child.get_link(currfile=self.origin.file))
                out.append(" " * indent + child_link)
        return out

    def get_markdown(self, controller):
        """
        Return the markdown for this section. This includes the section
        heading and the markdown for the children.
        """
        out = []
        out.append("---")
        out.append("")
        if self.subtitle:
            out.append("## {}".format(mkdn_esc(str(self))))
            out.extend(self.get_markdown_body(controller))
            out.append("")
        cnt = 0
        for child in self.children:
            chout = child.get_markdown(controller)
            if chout:
                cnt += 1
            if cnt > 1:
                out.append("---")
                out.append("")
            out.extend(chout)
        return out


class ItemBlock(LabelBlock):
    _paren_pat = re.compile(r'\([^\)]+\)')

    def __init__(self, title, subtitle, body, origin, parent=None):
        if self._paren_pat.search(subtitle):
            raise DocsGenException(title, "Text between parentheses, while declaring block:")
        super().__init__(title, subtitle, body, origin, parent=parent)
        self.example_num = 0
        self.deprecated = False
        self.topics = []
        self.aliases = []
        self.see_also = []

    def __str__(self):
        return "{}: {}".format(
            self.title.replace('&', '/'),
            re.sub(r'\([^\)]*\)', r'()', self.subtitle)
        )

    def get_data(self):
        d = super().get_data()
        if self.deprecated:
            d["deprecated"] = True
        d["topics"] = self.topics
        d["aliases"] = self.aliases
        d["see_also"] = self.see_also
        d["description"] = [
            line
            for item in self.get_children_by_title("Description")
            for line in item.body
        ]
        d["arguments"] = [
            line
            for item in self.get_children_by_title("Arguments")
            for line in item.body
        ]
        d["usages"] = [
            {
                "subtitle": item.subtitle,
                "body": item.body
            }
            for item in self.get_children_by_title("Usage")
        ]
        d["examples"] = [
            item.body
            for item in self.children if item.title.startswith("Example")
        ]
        skip_titles = ["Alias", "Aliases", "Arguments", "Description", "See Also", "Status", "Topics", "Usage"]
        d["children"] = list(filter(lambda x: not x["name"].startswith("Example"), d["children"]))
        d["children"] = list(filter(lambda x: x["name"] not in skip_titles, d["children"]))
        return d

    def get_markdown(self, controller):
        front_blocks = [
            ["Alias"],
            ["Aliases"],
            ["Status"],
            ["Topics"],
            ["Usage"]
        ]
        back_blocks = [
            ["See Also"],
            ["Example"]
        ]
        out = []
        out.append("### {}".format(mkdn_esc(str(self))))
        out.append("")
        for child in self.sort_children(front_blocks, back_blocks):
            out.extend(child.get_markdown(controller))
        return out


class ImageBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None, meta="", docs_dir=""):
        super().__init__(title, subtitle, body, origin, parent=parent)
        self.meta = meta
        self.image_num = 0
        self.image_url = None
        self.raw_script = []
        self.docs_dir = docs_dir
        self.image_req = None

        fileblock = self.parent
        while fileblock.parent:
            fileblock = fileblock.parent
        san_name = re.sub(r'[^A-Za-z0-9_]', r'', os.path.basename(parent.subtitle.strip()))
        file_ext = "gif" if "Spin" in meta or "Anim" in meta else "png"

        if parent is None:
            proposed_name = "{}.{}".format(san_name, file_ext)
        elif title == "Figure":
            parent.figure_num += 1
            self.image_num = parent.figure_num
            if parent.title in ["File", "LibFile"]:
                proposed_name = "figure{}.{}".format(self.image_num, file_ext)
            else:
                proposed_name = "{}_fig{}.{}".format(san_name, self.image_num, file_ext)
            self.title = "{} {}".format(self.title, self.image_num)
        else:
            parent.example_num += 1
            self.image_num = parent.example_num
            img_suffix = "_{}".format(self.image_num) if self.image_num > 1 else ""
            proposed_name = "{}{}.{}".format(san_name, img_suffix, file_ext)
            self.title = "{} {}".format(self.title, self.image_num)

        if "NORENDER" in meta:
            return

        show_img = (
            parent.title not in ("File", "LibFile", "Module", "Function&Module")
            and not any(x in meta for x in ("2D", "3D", "Spin", "Anim"))
        )
        if show_img:
            self.raw_script = self.body
            return

        file_base = os.path.splitext(fileblock.subtitle.strip())[0]
        self.image_url = os.path.join("images", file_base, proposed_name)
        script_lines = []
        script_lines.extend(fileblock.includes)
        script_lines.extend(fileblock.common_code)
        for line in body:
            if line.strip().startswith("--"):
                script_lines.append(line.strip()[2:])
            else:
                script_lines.append(line)
        self.raw_script = script_lines
        self.image_req = imgmgr.new_request(
            self.origin.file, self.origin.line,
            os.path.join(self.docs_dir, self.image_url),
            script_lines, meta,
            starting_cb=self._img_proc_start,
            completion_cb=self._img_proc_done
        )

    def get_data(self):
        d = super().get_data()
        d["script"] = self.raw_script
        d["imgurl"] = self.image_url
        return d

    def _img_proc_start(self, req):
        print("  {}... ".format(os.path.basename(self.image_url)), end='')
        sys.stdout.flush()

    def _img_proc_done(self, req):
        if req.success:
            if req.status == "SKIP":
                print()
            else:
                print(req.status)
            sys.stdout.flush()
            return
        pfx = "     "
        out = "Failed OpenSCAD script:\n"
        out += pfx + "Image: {}\n".format( os.path.basename(req.image_file) )
        out += pfx + "cmd-line = {}\n".format(" ".join(req.cmdline))
        for line in req.stdout:
            out += pfx + line + "\n"
        for line in req.stderr:
            out += pfx + line + "\n"
        out += pfx + "Return code = {}\n".format(req.return_code)
        out += pfx + ("-=" * 32) + "-\n"
        for line in req.script_lines:
            out += pfx + line + "\n"
        out += pfx + ("=-" * 32) + "="
        print("", file=sys.stderr)
        sys.stderr.flush()
        errorlog.add_entry(req.src_file, req.src_line, out, ErrorLog.FAIL)

    def get_markdown(self, controller):
        fileblock = self.parent
        while fileblock.parent:
            fileblock = fileblock.parent
        out = []
        if "Hide" in self.meta:
            return out
        out.append("<br/>")
        out.append("")
        out.append("**{}:** {}".format(mkdn_esc(self.title), mkdn_esc(self.subtitle)))
        out.append("")
        if "NORENDER" not in self.meta and self.image_url:
            out.append(
                '<img align="left" alt="{0} {1}" src="{2}">'
                .format(
                    mkdn_esc(self.parent.subtitle),
                    mkdn_esc(self.title),
                    self.image_url
                )
            )
            out.append("")
        if "Figure" in self.title:
            out.append('<br clear="all" />')
            out.append("")
        else:
            if self.image_req and self.image_req.script_under:
                out.append('<br clear="all" />')
                out.append("")
            out.extend(["    " + line for line in fileblock.includes])
            out.extend(["    " + line for line in self.body if not line.strip().startswith("--")])
            out.append("")
            if not self.image_req or not self.image_req.script_under:
                out.append('<br clear="all" />')
                out.append("")
        return out


class FigureBlock(ImageBlock):
    def __init__(self, title, subtitle, body, origin, parent, meta="", docs_dir=""):
        super().__init__(title, subtitle, body, origin, parent=parent, meta=meta, docs_dir=docs_dir)


class ExampleBlock(ImageBlock):
    def __init__(self, title, subtitle, body, origin, parent, meta="", docs_dir=""):
        super().__init__(title, subtitle, body, origin, parent=parent, meta=meta, docs_dir=docs_dir)


class ErrorLog(object):
    NOTE = "notice"
    WARN = "warning"
    FAIL = "error"

    REPORT_FILE = "docsgen_report.json"

    def __init__(self):
        self.errlist = []
        self.has_errors = False
        self.badfiles = {}

    def add_entry(self, file, line, msg, level):
        self.errlist.append( (file, line, msg, level) )
        self.badfiles[file] = 1
        print("!! {} at {}:{}: {}".format(level.upper(), file, line, msg) , file=sys.stderr)
        sys.stderr.flush()
        if level == self.FAIL:
            self.has_errors = True

    def write_report(self):
        report = [
            {
                "file": file,
                "line": line,
                "title": "DocsGen {}".format(level),
                "message": msg,
                "annotation_level": level
            }
            for file, line, msg, level in self.errlist
        ]
        with open(self.REPORT_FILE, "w") as f:
            f.write(json.dumps(report, sort_keys=True, indent=4))

    def file_has_errors(self, file):
        return file in self.badfiles

errorlog = ErrorLog()


class DocsGenParser(object):
    _header_pat = re.compile("^// ([A-Z][A-Za-z0-9_&-]*( ?[A-Z][A-Za-z0-9_&-]*)?)(\([^)]*\))?:( .*)?$")
    RCFILE = ".openscad_gendocs_rc"
    HASHFILE = ".source_hashes"

    def __init__(self, docs_dir="docs", strict=False, quiet=False):
        self.docs_dir = docs_dir.rstrip("/")
        self.strict = strict
        self.quiet = quiet
        self.file_blocks = []
        self.curr_file_block = None
        self.curr_section = None
        self.curr_item = None
        self.curr_parent = None
        self.ignored_file_pats = []
        self.ignored_files = {}
        self.priority_files = []
        self.items_by_name = {}
        self._reset_header_defs()
        self.read_hashes()

    def _sha256sum(self, filename):
        h = hashlib.sha256()
        b = bytearray(128*1024)
        mv = memoryview(b)
        try:
            with open(filename, 'rb', buffering=0) as f:
                for n in iter(lambda : f.readinto(mv), 0):
                    h.update(mv[:n])
        except FileNotFoundError as e:
            pass
        return h.hexdigest()

    def read_hashes(self):
        """Reads all known file hash values from the hashes file.
        """
        self.file_hashes = {}
        hashfile = os.path.join(self.docs_dir, self.HASHFILE)
        if os.path.isfile(hashfile):
            try:
                with open(hashfile, "r") as f:
                    for line in f.readlines():
                        filename, hashstr = line.strip().split("|")
                        self.file_hashes[filename] = hashstr
            except ValueError as e:
                print("Corrrupt hashes file.  Ignoring.", file=sys.stderr)
                sys.stderr.flush()
                self.file_hashes = {}

    def matches_hash(self, filename):
        """Returns True if the given file matches it's recorded hash value.
        Updates the hash value in memory for the file if it doesn't match.
        Does NOT save hash values to disk.
        """
        newhash = self._sha256sum(filename)
        if filename not in self.file_hashes:
            self.file_hashes[filename] = newhash
            return False
        oldhash = self.file_hashes[filename]
        if oldhash != newhash:
            self.file_hashes[filename] = newhash
            return False
        return True

    def write_hashes(self):
        """Writes out all known hash values.
        """
        hashfile = os.path.join(self.docs_dir, self.HASHFILE)
        os.makedirs(os.path.dirname(hashfile), exist_ok=True)
        with open(hashfile, "w") as f:
            for filename, hashstr in self.file_hashes.items():
                f.write("{}|{}\n".format(filename, hashstr))

    def _reset_header_defs(self):
        self.header_defs = {
            # BlockHeader:   (parenttype, nodetype, extras, callback)
            'Status':        ( ItemBlock, LabelBlock, None, self._status_block_cb ),
            'Alias':         ( ItemBlock, LabelBlock, None, self._alias_block_cb ),
            'Aliases':       ( ItemBlock, LabelBlock, None, self._alias_block_cb ),
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
        if os.path.exists(self.RCFILE):
            with open(self.RCFILE, "r") as f:
                lines = ["// " + line for line in f.readlines()]
                self.parse_lines(lines, src_file=self.RCFILE)

    def _status_block_cb(self, title, subtitle, body, origin, meta):
        self.curr_item.deprecated = "DEPRECATED" in subtitle

    def _alias_block_cb(self, title, subtitle, body, origin, meta):
        aliases = [x.strip() for x in subtitle.split(",")]
        self.curr_item.aliases.extend(aliases)
        for alias in aliases:
            self.items_by_name[alias] = self.curr_item

    def _skip_lines(self, lines, line_num=0):
        while line_num < len(lines):
            line = lines[line_num]
            match = self._header_pat.match(line)
            if match:
                return line_num
            line_num += 1
        return line_num

    def _files_prioritized(self):
        out = []
        found = {}
        for pri_file in self.priority_files:
            for file_block in self.file_blocks:
                if file_block.subtitle == pri_file:
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
            self.header_defs[title] = (parentspec, NumberedListBlock, None, None)
        elif "BulletList" in meta:
            self.header_defs[title] = (parentspec, BulletListBlock, None, None)
        elif "Table:" in meta:
            hdr_meta = meta.split("Table:",1)[1].split("||")
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

    def _mkfilenode(self, origin):
        if not self.curr_file_block:
            self.curr_file_block = FileBlock("LibFile", origin.file, [], origin)
            self.curr_parent = self.curr_file_block
            self.file_blocks.append(self.curr_file_block)

    def _parse_block(self, lines, line_num=0, src_file=None):
        line_num = self._skip_lines(lines, line_num)
        if line_num >= len(lines):
            return line_num
        hdr_line_num = line_num
        line = lines[line_num]
        match = self._header_pat.match(line)
        if not match:
            return line_num
        title = match.group(1)
        meta = match.group(3)[1:-1] if match.group(3) else ""
        subtitle = match.group(4).strip() if match.group(4) else ""
        body = []
        line_num += 1

        first_line = True
        indent = 2
        while line_num < len(lines):
            line = lines[line_num]
            if not line.startswith("//" + (" " * indent)):
                if line.startswith("//  "):
                    raise DocsGenException(title, "Body line has less indentation than first line, while declaring block:")
                break
            line = line[2:]
            if first_line:
                first_line = False
                indent = len(line) - len(line.lstrip())
            line = line[indent:]
            body.append(line.rstrip())
            line_num += 1

        try:
            parent = self.curr_parent
            origin = OriginInfo(src_file, hdr_line_num+1)
            if title == "DefineHeader":
                self._define_blocktype(subtitle, meta)
            elif title == "IgnoreFiles":
                if origin.file != self.RCFILE:
                    raise DocsGenException(title, "Block disallowed outside of {} file:".format(self.RCFILE))
                if subtitle:
                    body.insert(0,subtitle)
                self.ignored_file_pats.extend([
                    fname.strip() for fname in body
                ])
                self.ignored_files = {}
                for pat in self.ignored_file_pats:
                    files = glob.glob(pat,recursive=True)
                    for fname in files:
                        self.ignored_files[fname] = True
            elif title == "PrioritizeFiles":
                if origin.file != self.RCFILE:
                    raise DocsGenException(title, "Block disallowed outside of {} file:".format(self.RCFILE))
                if subtitle:
                    body.insert(0,subtitle)
                self.priority_files = [x.strip() for x in body]
            elif title == "DocsDirectory":
                if origin.file != self.RCFILE:
                    raise DocsGenException(title, "Block disallowed outside of {} file:".format(self.RCFILE))
                if body:
                    raise DocsGenException(title, "Body not supported, while declaring block:")
                self.docs_dir = subtitle.strip().rstrip("/")
            elif title == "vim" or title == "emacs":
                pass  # Ignore vim and emacs modelines
            elif title in ["File", "LibFile"]:
                if self.curr_file_block:
                    raise DocsGenException(title, "File/Libfile block already specified, while declaring block:")
                self.curr_file_block = FileBlock(title, subtitle, body, origin)
                self.curr_parent = self.curr_file_block
                self.file_blocks.append(self.curr_file_block)
            elif not self.curr_file_block and self.strict:
                raise DocsGenException(title, "Must declare File or LibFile block before declaring block:")

            elif title == "Section":
                self._mkfilenode(origin)
                self.curr_section = SectionBlock(title, subtitle, body, origin, parent=self.curr_file_block)
                self.curr_parent = self.curr_section
            elif title == "Includes":
                self._mkfilenode(origin)
                IncludesBlock(title, subtitle, body, origin, parent=self.curr_file_block)
            elif title == "CommonCode":
                self._mkfilenode(origin)
                self.curr_file_block.common_code.extend(body)
            elif title == "Figure":
                self._mkfilenode(origin)
                FigureBlock(title, subtitle, body, origin, parent=parent, meta=meta, docs_dir=self.docs_dir)
            elif title == "Example":
                self._mkfilenode(origin)
                ExampleBlock(title, subtitle, body, origin, parent=parent, meta=meta, docs_dir=self.docs_dir)
            elif title == "Figures":
                self._mkfilenode(origin)
                for lnum, line in enumerate(body):
                    FigureBlock(title[:-1], subtitle, [line], origin, parent=parent, meta=meta, docs_dir=self.docs_dir)
            elif title == "Examples":
                self._mkfilenode(origin)
                for lnum, line in enumerate(body):
                    ExampleBlock(title[:-1], subtitle, [line], origin, parent=parent, meta=meta, docs_dir=self.docs_dir)
            elif title in self.header_defs:
                parcls, cls, data, cb = self.header_defs[title]
                if parcls and not isinstance(self.curr_parent, parcls):
                    raise DocsGenException(title, "Must be in Function/Module/Constant while declaring block:")
                if cls in (GenericBlock, LabelBlock, TextBlock, NumberedListBlock, BulletListBlock):
                    cls(title, subtitle, body, origin, parent=parent)
                elif cls == TableBlock:
                    cls(title, subtitle, body, origin, parent=parent, header_sets=data)
                elif cls in (FigureBlock, ExampleBlock):
                    cls(title, subtitle, body, origin, parent=parent, meta=meta, docs_dir=self.docs_dir)
                if cb:
                    cb(title, subtitle, body, origin, meta)

            elif title in ["Constant", "Function", "Module", "Function&Module"]:
                self._mkfilenode(origin)
                if not self.curr_section:
                    self.curr_section = SectionBlock("Section", "", [], origin, parent=self.curr_file_block)
                    self.curr_parent = self.curr_section
                if subtitle in self.items_by_name:
                    prevorig = self.items_by_name[subtitle].origin
                    msg = "Previous declaration of `{}` at {}:{}, Redeclared:".format(subtitle, prevorig.file, prevorig.line)
                    raise DocsGenException(title, msg)
                item = ItemBlock(title, subtitle, body, origin, parent=self.curr_section)
                self.items_by_name[subtitle] = item
                self.curr_item = item
                self.curr_parent = item
            elif title == "Topics":
                if not self.curr_item:
                    raise DocsGenException(title, "Must be in Function/Module/Constant while declaring block:")
                TopicsBlock(title, subtitle, body, origin, parent=parent)
            elif title == "See Also":
                if not self.curr_item:
                    raise DocsGenException(title, "Must be in Function/Module/Constant while declaring block:")
                SeeAlsoBlock(title, subtitle, body, origin, parent=parent)
            else:
                raise DocsGenException(title, "Unrecognized block:")

            if line_num < len(lines) and not lines[line_num].startswith("//"):
                self.curr_item = None
            line_num = self._skip_lines(lines, line_num)

        except DocsGenException as e:
            errorlog.add_entry(origin.file, origin.line, str(e), ErrorLog.FAIL)

        return line_num

    def get_indexed_names(self):
        """Returns the list of all indexable function/module/constants  by name, in alphabetical order.
        """
        lst = sorted(self.items_by_name.keys())
        for item in lst:
            yield item

    def get_indexed_data(self, name):
        """Given the name of an indexable function/module/constant, returns the parsed data dictionary for that item's documentation.

        Example Results
        ---------------
        {
            "name": "Function&Module",
            "subtitle": "foobar()",
            "body": [],
            "file": "foobar.scad",
            "line": 23,
            "topics": ["Testing", "Metasyntactic"],
            "aliases": ["foob()", "feeb()"],
            "see_also": ["barbaz()", "bazqux()"],
            "usages": [
                {
                    "subtitle": "As function",
                    "body": [
                        "val = foobar(a, b, <c>);",
                        "list = foobar(d, b=);"
                    ]
                }, {
                    "subtitle": "As module",
                    "body": [
                        "foobar(a, b, <c>);",
                        "foobar(d, b=);"
                    ]
                }
            ],
            "description": [
                "When called as a function, this returns the foo of bar.",
                "When called as a module, renders a foo as modified by bar."
            ],
            "arguments": [
                "a = The a argument.",
                "b = The b argument.",
                "c = The c argument.",
                "d = The d argument."
            ],
            "examples": [
                [
                    "foobar(5, 7)"
                ], [
                    "x = foobar(5, 7);",
                    "echo(x);"
                ]
            ]
            "children": [
                {
                    "name": "Extra Anchors",
                    "subtitle": "",
                    "body": [
                        "\"fee\" = Anchors at the fee position.",
                        "\"fie\" = Anchors at the fie position."
                    ]
                }
            ]
        }
        """
        if name in self.items_by_name:
            return self.items_by_name[name].get_data()
        return {}

    def get_all_data(self):
        """Gets all the documentation data parsed so far.

        Sample Results
        ----------
        [
            {
                "name": "LibFile",
                "subtitle":"foobar.scad",
                "body": [
                    "This is the first line of the LibFile body.",
                    "This is the second line of the LibFile body."
                ],
                "includes": [
                    "include <foobar.scad>",
                    "include <bazqux.scad>"
                ],
                "commoncode": [
                    "$fa = 2;",
                    "$fs = 2;"
                ],
                "children": [
                    {
                        "name": "Section",
                        "subtitle": "Metasyntactical Calls",  // If subtitle is "", section is just a placeholder.
                        "body": [
                            "This is the first line of the body of the Section.",
                            "This is the second line of the body of the Section."
                        ],
                        "children": [
                            {
                                "name": "Function&Module",
                                "subtitle": "foobar()",
                                "body": [],
                                "file": "foobar.scad",
                                "line": 23,
                                "topics": ["Testing", "Metasyntactic"],
                                "aliases": ["foob()", "feeb()"],
                                "see_also": ["barbaz()", "bazqux()"],
                                "usages": [
                                    {
                                        "subtitle": "As function",
                                        "body": [
                                            "val = foobar(a, b, <c>);",
                                            "list = foobar(d, b=);"
                                        ]
                                    }, {
                                        "subtitle": "As module",
                                        "body": [
                                            "foobar(a, b, <c>);",
                                            "foobar(d, b=);"
                                        ]
                                    }
                                ],
                                "description": [
                                    "When called as a function, this returns the foo of bar.",
                                    "When called as a module, renders a foo as modified by bar."
                                ],
                                "arguments": [
                                    "a = The a argument.",
                                    "b = The b argument.",
                                    "c = The c argument.",
                                    "d = The d argument."
                                ],
                                "examples": [
                                    [
                                        "foobar(5, 7)"
                                    ],
                                    [
                                        "x = foobar(5, 7);",
                                        "echo(x);"
                                    ],
                                    // ... Next Example
                                ]
                                "children": [
                                    {
                                        "name": "Extra Anchors",
                                        "subtitle": "",
                                        "body": [
                                            "\"fee\" = Anchors at the fee position.",
                                            "\"fie\" = Anchors at the fie position."
                                        ]
                                    }
                                ]
                            },
                            // ... next function/module/constant
                        ]
                    },
                    // ... next section
                ]
            },
            // ... next file
        ]
        """
        return [
            fblock.get_data()
            for fblock in self.file_blocks
        ]

    def parse_lines(self, lines, line_num=0, src_file=None):
        """Parses the given list of strings for documentation comments.

        Parameters
        ----------
        lines : list of str
            The list of strings to parse for documentation comments.
        line_num : int
            The current index into the list of strings of the current line to parse.
        src_file : str
            The name of the source file that this is from.  This is used just for error reporting.
            If true, generates images for example scripts, by running them in OpenSCAD.
        """
        while line_num < len(lines):
            line_num = self._parse_block(lines, line_num, src_file=src_file)

    def parse_file(self, filename, commentless=False, images=True, test_only=False, force=False):
        """Parses the given file for documentation comments.

        Parameters
        ----------
        filename : str
            The name of the file to parse documentaiton comments from.
        commentless : bool
            If true, treat every line of the file as if it starts with '// '.  This is used for reading docsgen config files.
        images : bool
            If true, generates images for example scripts, by running them in OpenSCAD.
        test_only: bool
            If true, validates example scripts in OpenSCAD, but does not generate images.
        force : bool
            If true, forces image generation, even if the source file is unchanged from last run.
        """
        if filename in self.ignored_files:
            return
        if not self.quiet:
            print("{}:".format(filename))
        self.curr_file_block = None
        self.curr_section = None
        self._reset_header_defs()
        with open(filename, "r") as f:
            if commentless:
                lines = ["// " + line for line in f.readlines()]
            else:
                lines = f.readlines()
            self.parse_lines(lines, src_file=filename)
        if images:
            hashmatch = self.matches_hash(filename)
            if force or not hashmatch:
                imgmgr.process_requests(test_only=test_only)
            else:
                imgmgr.purge_requests()
            if not test_only:
                if errorlog.file_has_errors(filename):
                    self.file_hashes.pop(filename)
                self.write_hashes()

    def parse_files(self, filenames, commentless=False, images=True, test_only=False, force=False):
        """Parses all of the given files for documentation comments.

        Parameters
        ----------
        filenames : list of str
            The list of filenames to parse documentaiton comments from.
        commentless : bool
            If true, treat every line of the files as if they starts with '// '.  This is used for reading docsgen config files.
        images : bool
            If true, generates images for example scripts, by running them in OpenSCAD.
        test_only: bool
            If true, validates example scripts in OpenSCAD, but does not generate images.
        force : bool
            If true, forces image generation, even if the source file is unchanged from last run.
        """
        for filename in filenames:
            self.parse_file(
                filename,
                commentless=commentless,
                images=images,
                test_only=test_only,
                force=force
            )

    def dump_tree(self, nodes, pfx="", maxdepth=6):
        """Dumps debug info to stdout for parsed documentation subtree."""
        if maxdepth <= 0 or not nodes:
            return
        for node in nodes:
            print("{}{}".format(pfx,node))
            for line in node.body:
                print("  {}{}".format(pfx,line))
            self.dump_tree(node.children, pfx=pfx+"  ", maxdepth=maxdepth-1)

    def dump_full_tree(self):
        """Dumps debug info to stdout for all parsed documentation."""
        self.dump_tree(self.file_blocks)

    def write_markdown_docsfiles(self, testonly=False):
        """Generates the .md files for each source file that has been parsed.

        Parameters
        ----------
        testonly : bool
            If True, then all image scripts are parsed in test-only mode, which checks for script errors, but doesn't generate actual images.
        """
        if testonly:
            for fblock in self.file_blocks:
                lines = fblock.get_markdown(self)
            return
        os.makedirs(self.docs_dir, mode=0o744, exist_ok=True)
        for fblock in self.file_blocks:
            filename = fblock.subtitle
            outfile = os.path.join(self.docs_dir, filename+".md")
            if not self.quiet:
                print("Writing {}...".format(outfile))
            outdir = os.path.dirname(outfile)
            if not os.path.exists(outdir):
                os.makedirs(outdir, mode=0o744, exist_ok=True)
            with open(outfile,"w") as f:
                for line in fblock.get_markdown(self):
                    f.write(line + "\n")

    def write_toc_file(self):
        """Generates the table-of-contents TOC.md file from the parsed documentation"""
        os.makedirs(self.docs_dir, mode=0o744, exist_ok=True)
        out = []
        out.append("# Table of Contents")
        out.append("")
        pri_blocks = self._files_prioritized()
        for fnum, fblock in enumerate(pri_blocks):
            out.append("{}. {}".format(fnum+1, fblock.get_link(label=fblock.subtitle, literalize=False)))
            sects = [
                sect for sect in fblock.children
                if isinstance(sect, SectionBlock)
            ]
            for sect in sects:
                ind = "    "
                if sect.subtitle:
                    out.append("    - {}:  ".format(sect.get_link(label=sect.subtitle, literalize=False)))
                    ind += "    "
                items = [
                    item for item in sect.children
                    if isinstance(item, ItemBlock)
                ]
                out.append(ind + (" ".join(item.get_link() for item in items)))
        outfile = os.path.join(self.docs_dir, "TOC.md")
        if not self.quiet:
            print("Writing {}...".format(outfile))
        with open(outfile, "w") as f:
            for line in out:
                f.write(line + "\n")

    def write_topics_file(self):
        """Generates the Topics.md file from the parsed documentation."""
        os.makedirs(self.docs_dir, mode=0o744, exist_ok=True)
        index_by_letter = {}
        for file_block in self.file_blocks:
            for section in file_block.children:
                if not isinstance(section,SectionBlock):
                    continue
                for item in section.children:
                    if not isinstance(item,ItemBlock):
                        continue
                    names = [item.subtitle]
                    names.extend(item.aliases)
                    for topic in item.topics:
                        ltr = "0" if not topic[0].isalpha() else topic[0].upper()
                        if ltr not in index_by_letter:
                            index_by_letter[ltr] = {}
                        if topic not in index_by_letter[ltr]:
                            index_by_letter[ltr][topic] = []
                        for name in names:
                            index_by_letter[ltr][topic].append( (name, item) )

        ltrs_found = sorted(index_by_letter.keys())
        out = []
        out.append("# Topics Index")
        out.append("An index of topics, with related functions, modules, and constants.")
        out.append("")
        out.append("")
        for ltr in ltrs_found:
            topics = sorted(index_by_letter[ltr].keys())
            out.append(
                "- [{0}](#{0}): {1}".format(
                    ltr,
                    ", ".join(
                        "[{0}](#{1})".format(mkdn_esc(topic), header_link(topic))
                        for topic in topics
                    )
                )
            )
        out.append("")

        for ltr in ltrs_found:
            topics = sorted(index_by_letter[ltr].keys())
            out.append("---")
            out.append("### {}".format(ltr))
            out.append("")
            for topic in topics:
                itemlist = index_by_letter[ltr][topic]
                out.append("#### {}:".format(topic))
                sorted_items = sorted(itemlist, key=lambda x: x[0].lower())
                for name, item in sorted_items:
                    out.append(
                        "- {} (in {})".format(
                            item.get_link(label=name),
                            mkdn_esc(item.origin.file)
                        )
                    )
                out.append("")
        outfile = os.path.join(self.docs_dir, "Topics.md")
        if not self.quiet:
            print("Writing {}...".format(outfile))
        with open(outfile, "w") as f:
            for line in out:
                f.write(line + "\n")

    def write_index_file(self):
        """Generates the alphabetical function/module/constant Index.md file from the parsed documentation."""
        os.makedirs(self.docs_dir, mode=0o744, exist_ok=True)
        unsorted_items = []
        for file_block in self.file_blocks:
            sections = [
                sect for sect in file_block.children
                if isinstance(sect, SectionBlock)
            ]
            for sect in sections:
                items = [
                    item for item in sect.children
                    if isinstance(item, ItemBlock)
                ]
                for item in items:
                    names = [item.subtitle]
                    names.extend(item.aliases)
                    for name in names:
                        unsorted_items.append( (name, item) )
        sorted_items = sorted(unsorted_items, key=lambda x: x[0].lower())
        index_by_letter = {}
        for name, item in sorted_items:
            ltr = "0" if not name[0].isalpha() else name[0].upper()
            if ltr not in index_by_letter:
                index_by_letter[ltr] = []
            index_by_letter[ltr].append( (name, item ) )
        ltrs_found = sorted(index_by_letter.keys())
        out = []
        out.append("# Alphabetical Index")
        out.append("An index of Functions, Modules, and Constants by name.")
        out.append("")
        out.append(" ".join(["[{0}](#{0}) ".format(ltr) for ltr in ltrs_found]))
        out.append("")
        for ltr in ltrs_found:
            out.append("---")
            out.append("### {}".format(ltr))
            for name, item in index_by_letter[ltr]:
                out.append(
                    "- {} (in {})".format(
                        item.get_link(label=name),
                        mkdn_esc(item.origin.file)
                    )
                )
            out.append("")
        outfile = os.path.join(self.docs_dir, "Index.md")
        if not self.quiet:
            print("Writing {}...".format(outfile))
        with open(outfile, "w") as f:
            for line in out:
                f.write(line + "\n")

    def write_cheatsheet_file(self):
        """Generates the CheatSheet.md file from the parsed documentation."""
        os.makedirs(self.docs_dir, mode=0o744, exist_ok=True)
        out = []
        out.append("# The BOSL2 Cheat Sheet")
        out.append("")
        pri_blocks = self._files_prioritized()
        for file_block in pri_blocks:
            file_shown = False
            for section in file_block.children:
                if not isinstance(section,SectionBlock):
                    continue
                sect_shown = False
                consts = []
                for item in section.children:
                    if not isinstance(item,ItemBlock):
                        continue
                    if item.title != "Constant":
                        continue
                    names = [item.subtitle]
                    names.extend(item.aliases)
                    for name in names:
                        consts.append(item.get_link(label=name))
                lines = []
                for item in section.children:
                    if not isinstance(item,ItemBlock):
                        continue
                    if item.title == "Constant":
                        continue
                    item_name = re.sub(r'[^A-Za-z0-9_$]', r'', item.subtitle)
                    link = item.get_link(label=item_name, literalize=False)
                    usages = [
                        usage
                        for usage in item.children
                        if usage.title == "Usage"
                    ]
                    oline = ""
                    for usage in usages:
                        for line in usage.body:
                            line = mkdn_esc(line).replace(mkdn_esc(item_name),link)
                            oline += "<code>{}</code>  ".format(line)
                    if oline:
                        lines.append(oline)

                if consts or lines:
                    if not file_shown:
                        out.append("---")
                        out.append("### {}".format(mkdn_esc(str(file_block))))
                        file_shown = True
                    if not sect_shown:
                        out.append("#### {}".format(mkdn_esc(str(section))))
                        sect_shown = True
                if consts:
                    out.append("Constants: " + (" ".join(mkdn_esc(x) for x in consts)))
                for line in lines:
                    out.append(line)
            out.append("")
        outfile = os.path.join(self.docs_dir, "CheatSheet.md")
        if not self.quiet:
            print("Writing {}...".format(outfile))
        with open(outfile, "w") as f:
            for line in out:
                f.write(line + "\n")


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
