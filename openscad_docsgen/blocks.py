from __future__ import print_function

import os
import os.path
import re
import sys

from .utils import flatten
from .errorlog import ErrorLog, errorlog
from .imagemanager import image_manager


class DocsGenException(Exception):
    def __init__(self, block="", message=""):
        self.block = block
        self.message = message
        super().__init__('{} "{}"'.format(self.message, self.block))


class GenericBlock(object):
    _link_pat = re.compile(r'^(.*?)\{\{([A-Za-z0-9_()]+)\}\}(.*)$')

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

    def get_children_by_title(self, titles):
        if isinstance(titles,str):
            titles = [titles]
        return [
            child
            for child in self.children
            if child.title in titles
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

    def get_link(self, target, currfile=None):
        return self.title

    def parse_links(self, line, controller, target):
        oline = ""
        while line:
            m = self._link_pat.match(line)
            if m:
                oline += m.group(1)
                name = m.group(2)
                line = m.group(3)
                if name not in controller.items_by_name:
                    msg = "Invalid Link {{{{{0}}}}}".format(name)
                    errorlog.add_entry(self.origin.file, self.origin.line, msg, ErrorLog.FAIL)
                    oline += name
                else:
                    item = controller.items_by_name[name]
                    oline += item.get_link(target, currfile=self.origin.file)
            else:
                oline += line
                line = ""
        return oline

    def get_markdown_body(self, controller, target):
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
                out.append(self.parse_links(line, controller, target))
        return out

    def get_tocfile_lines(self, target, n=1, currfile=""):
        return []

    def get_toc_lines(self, target, n=1, currfile=""):
        return []

    def get_cheatsheet_lines(self, controller, target):
        return []

    def get_file_lines(self, controller, target):
        sub = self.parse_links(self.subtitle, controller, target)
        out = target.block_header(self.title, sub)
        out.extend(self.get_markdown_body(controller, target))
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

    def get_file_lines(self, controller, target):
        links = [
            target.get_link(topic, anchor=target.header_link(topic), file="Topics", literalize=False)
            for topic in self.topics
        ]
        links = ", ".join(links)
        out = target.block_header(self.title, links)
        return out


class SeeAlsoBlock(LabelBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)

    def get_file_lines(self, controller, target):
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
        links = [
            item.get_link(target, currfile=self.origin.file, literalize=False)
            for item in items
        ]
        out = []
        links = ", ".join(links)
        out.extend(target.block_header(self.title, links, escsub=False))
        return out


class HeaderlessBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        if subtitle:
            body.insert(0, subtitle)
            subtitle = ""
        super().__init__(title, subtitle, body, origin, parent=parent)

    def get_file_lines(self, controller, target):
        out = []
        out.append("")
        out.extend(self.get_markdown_body(controller, target))
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

    def get_file_lines(self, controller, target):
        sub = self.parse_links(self.subtitle, controller, target)
        sub = target.escape_entities(sub)
        out = target.block_header(self.title, sub)
        out.extend(target.bullet_list(self.body))
        return out


class NumberedListBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)

    def get_file_lines(self, controller, target):
        sub = self.parse_links(self.subtitle, controller, target)
        sub = target.escape_entities(sub)
        out = target.block_header(self.title, sub)
        out.extend(target.numbered_list(self.body))
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

    def get_file_lines(self, controller, target):
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
            cells = [
                self.parse_links(x.strip(), controller, target)
                for x in line.split("=",len(hdr_set)-1)
            ]
            table.append(cells)
        if table:
            tables.append(table)
        sub = self.parse_links(self.subtitle, controller, target)
        sub = target.escape_entities(sub)
        out = target.block_header(self.title, sub)
        for tnum, table in enumerate(tables):
            headers = self.header_sets[tnum]
            out.extend(target.table(headers,table))
        return out


class FileBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin):
        super().__init__(title, subtitle, body, origin)
        self.includes = []
        self.common_code = []
        self.footnotes = []
        self.summary = ""
        self.group = ""

    def get_data(self):
        d = super().get_data()
        d["includes"] = self.includes
        d["commoncode"] = self.common_code
        d["group"] = self.group
        d["summary"] = self.summary
        d["footnotes"] = [
            {
                "mark": mark,
                "note": note
            } for mark, note in self.footnotes
        ]
        skip_titles = ["CommonCode", "Includes"]
        d["children"] = list(filter(lambda x: x["name"] not in skip_titles, d["children"]))
        return d

    def get_link(self, target, currfile=None, label=""):
        file = self.origin.file
        if currfile is None or self.origin.file == currfile:
            file = ""
        return target.get_link(
            label=label if label else str(self),
            anchor="",
            file=file,
            literalize=False
        )

    def get_tocfile_lines(self, target, n=1, currfile=""):
        sections = [
            sect for sect in self.children
            if isinstance(sect, SectionBlock)
        ]
        link = self.get_link(target, label=self.subtitle, currfile=currfile)
        out = []
        out.extend(target.header("{}. {}".format(n, link), lev=target.SECTION, esc=False))
        if self.summary:
            out.extend(target.line_with_break(self.summary))
        if self.footnotes:
            for mark, note, origin in self.footnotes:
                out.extend(target.line_with_break(target.italics(note)))
        out.extend(target.bullet_list_start())
        for n, sect in enumerate(sections):
            out.extend(sect.get_tocfile_lines(target, n=n+1, currfile=currfile))
        out.extend(target.bullet_list_end())
        return out

    def get_toc_lines(self, target, n=1, currfile=""):
        sections = [
            sect for sect in self.children
            if isinstance(sect, SectionBlock)
        ]
        out = []
        out.extend(target.numbered_list_start())
        for n, sect in enumerate(sections):
            out.extend(sect.get_toc_lines(target, n=n+1, currfile=currfile))
        out.extend(target.numbered_list_end())
        return out

    def get_cheatsheet_lines(self, controller, target):
        lines = []
        for child in self.get_children_by_title("Section"):
            lines.extend(child.get_cheatsheet_lines(controller, target))
        out = []
        if lines:
            out.extend(target.header("{}: {}".format(self.title, self.subtitle), lev=target.SUBSECTION))
            out.extend(lines)
        return out

    def get_file_lines(self, controller, target):
        out = target.header(str(self), lev=target.FILE)
        out.extend(target.markdown_block(self.get_markdown_body(controller, target)))
        for child in self.children:
            if not isinstance(child, SectionBlock):
                out.extend(child.get_file_lines(controller, target))
        out.extend(target.header("Table of Contents", lev=target.SECTION))
        out.extend(self.get_toc_lines(target, currfile=self.origin.file))
        for child in self.children:
            if isinstance(child, SectionBlock):
                out.extend(child.get_file_lines(controller, target))
        return out


class IncludesBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)
        if parent:
            parent.includes.extend(body)

    def get_file_lines(self, controller, target):
        out = []
        if self.body:
            out.extend(target.markdown_block([
                "To use, add the following lines to the beginning of your file:"
            ]))
            out.extend(target.markdown_block(target.indent_lines(self.body)))
        return out


class SectionBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)

    def get_link(self, target, currfile=None, label=""):
        file = self.origin.file
        if currfile is None or self.origin.file == currfile:
            file = ""
        return target.get_link(
            label=label if label else str(self),
            anchor=target.header_link(str(self)),
            file=file,
            literalize=False
        )

    def get_tocfile_lines(self, target, n=1, currfile=""):
        """
        Return the markdown table of contents lines for the children in this
        section. This is returned as a series of bullet points.
        `indent` sets the level of indentation for the bullet points
        """
        out = []
        if self.subtitle:
            item = self.get_link(target, label=self.subtitle, currfile=currfile)
            out.extend(target.line_with_break(target.bullet_list_item(item)))
            subsects = self.get_children_by_title("Subsection")
            if subsects:
                out.extend(target.bullet_list_start())
                for child in subsects:
                    out.extend(target.indent_lines(child.get_tocfile_lines(target, currfile=currfile)))
                out.extend(target.bullet_list_end())
            out.extend(
                target.indent_lines([
                    " ".join(
                        " ".join(child.get_tocfile_lines(target, currfile=currfile))
                        for child in self.get_children_by_title(
                            ["Constant","Function","Module","Function&Module"]
                        )
                    )
                ])
            )
        else:
            for child in self.get_children_by_title("Subsection"):
                out.extend(child.get_tocfile_lines(target, currfile=currfile))
            out.append(" ".join(
                " ".join(child.get_tocfile_lines(target, currfile=currfile))
                for child in self.get_children_by_title(
                    ["Constant","Function","Module","Function&Module"]
                )
            ))
        return out

    def get_toc_lines(self, target, n=1, currfile=""):
        """
        Return the markdown table of contents lines for the children in this
        section. This is returned as a series of bullet points.
        `indent` sets the level of indentation for the bullet points
        """
        lines = []
        subsects = self.get_children_by_title("Subsection")
        if subsects:
            lines.extend(target.numbered_list_start())
            for num, child in enumerate(subsects):
                lines.extend(child.get_toc_lines(target, currfile=currfile, n=num+1))
            lines.extend(target.numbered_list_end())
        for child in self.get_children_by_title(["Constant","Function","Module","Function&Module"]):
            lines.extend(child.get_toc_lines(target, currfile=currfile))
        out = []
        if self.subtitle:
            item = self.get_link(target, currfile=currfile)
            out.extend(target.numbered_list_item(n, item))
            out.extend(target.bullet_list_start())
            out.extend(target.indent_lines(lines))
            out.extend(target.bullet_list_end())
        else:
            out.extend(target.bullet_list_start())
            out.extend(lines)
            out.extend(target.bullet_list_end())
        return out

    def get_cheatsheet_lines(self, controller, target):
        subs = []
        for child in self.get_children_by_title("Subsection"):
            subs.extend(child.get_cheatsheet_lines(controller, target))
        consts = []
        for cnst in self.get_children_by_title("Constant"):
            consts.append(cnst.get_link(target, currfile="CheatSheet"))
            for alias in cnst.aliases:
                consts.append(cnst.get_link(target, label=alias, currfile="CheatSheet"))
        items = []
        for child in self.get_children_by_title(["Function","Module","Function&Module"]):
            items.extend(child.get_cheatsheet_lines(controller, target))
        out = []
        if subs or consts or items:
            out.extend(target.header("{}: {}".format(self.title, self.subtitle), lev=target.ITEM))
            out.extend(subs)
            if consts:
                out.append("Constants: " + " ".join(consts))
            out.extend(items)
            out.append("")
        return out

    def get_file_lines(self, controller, target):
        """
        Return the markdown for this section. This includes the section
        heading and the markdown for the children.
        """
        out = []
        if self.subtitle:
            out.extend(target.header(str(self), lev=target.SECTION))
            out.extend(target.markdown_block(self.get_markdown_body(controller, target)))
        for child in self.children:
            out.extend(child.get_file_lines(controller, target))
        return out


class SubsectionBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None):
        super().__init__(title, subtitle, body, origin, parent=parent)

    def get_link(self, target, currfile=None, label=""):
        file = self.origin.file
        if currfile is None or self.origin.file == currfile:
            file = ""
        return target.get_link(
            label=label if label else str(self),
            anchor=target.header_link(str(self)),
            file=file,
            literalize=False
        )

    def get_tocfile_lines(self, target, n=1, currfile=""):
        """
        Return the markdown table of contents lines for the children in this
        subsection. This is returned as a series of bullet points.
        `indent` sets the level of indentation for the bullet points
        """
        out = []
        item = self.get_link(target, label=self.subtitle, currfile=currfile)
        out.extend(target.bullet_list_item(item))
        items = self.get_children_by_title(["Constant","Function","Module","Function&Module"])
        if items:
            out.extend(
                target.indent_lines([
                    " ".join(
                        " ".join(child.get_tocfile_lines(target, currfile=currfile))
                        for child in items
                    )
                ])
            )
        return out

    def get_toc_lines(self, target, n=1, currfile=""):
        """
        Return the markdown table of contents lines for the children in this
        subsection. This is returned as a series of bullet points.
        `indent` sets the level of indentation for the bullet points
        """
        lines = []
        for child in self.get_children_by_title(["Constant","Function","Module","Function&Module"]):
            lines.extend(child.get_toc_lines(target, currfile=currfile))
        out = []
        if self.subtitle:
            item = self.get_link(target, currfile=currfile)
            out.extend(target.numbered_list_item(n, item))
            if lines:
                out.extend(target.bullet_list_start())
                out.extend(target.indent_lines(lines))
                out.extend(target.bullet_list_end())
        elif lines:
            out.extend(target.bullet_list_start())
            out.extend(lines)
            out.extend(target.bullet_list_end())
        return out

    def get_cheatsheet_lines(self, controller, target):
        consts = []
        for cnst in self.get_children_by_title("Constant"):
            consts.append(cnst.get_link(target, currfile="CheatSheet"))
            for alias in cnst.aliases:
                consts.append(cnst.get_link(target, label=alias, currfile="CheatSheet"))
        items = []
        for child in self.get_children_by_title(["Function","Module","Function&Module"]):
            items.extend(child.get_cheatsheet_lines(controller, target))
        out = []
        if consts or items:
            out.extend(target.header("{}: {}".format(self.title, self.subtitle), lev=target.ITEM))
            if consts:
                out.append("Constants: " + " ".join(consts))
            out.extend(items)
            out.append("")
        return out

    def get_file_lines(self, controller, target):
        """
        Return the markdown for this section. This includes the section
        heading and the markdown for the children.
        """
        out = []
        if self.subtitle:
            out.extend(target.header(str(self), lev=target.SUBSECTION))
            out.extend(target.markdown_block(self.get_markdown_body(controller, target)))
        for child in self.children:
            out.extend(child.get_file_lines(controller, target))
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

    def get_link(self, target, currfile=None, label="", literalize=True):
        file = self.origin.file
        if currfile is None or self.origin.file == currfile:
            file = ""
        return target.get_link(
            label=label if label else self.subtitle,
            anchor=target.header_link(
                "{}: {}".format(self.title, self.subtitle)
            ),
            file=file,
            literalize=literalize
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
        d["children"] = list(filter(lambda x: x["name"] not in skip_titles and not x["name"].startswith("Example"), d["children"]))
        return d

    def get_tocfile_lines(self, target, n=1, currfile=""):
        out = [self.get_link(target, currfile=currfile)]
        return out

    def get_toc_lines(self, target, n=1, currfile=""):
        out = target.bullet_list_item(self.get_link(target, currfile=currfile))
        return out

    def get_cheatsheet_lines(self, controller, target):
        oline = ""
        item_name = re.sub(r'[^A-Za-z0-9_$]', r'', self.subtitle)
        link = self.get_link(target, currfile="CheatSheet", label=item_name, literalize=False)
        parts = []
        part_lens = []
        for usage in self.get_children_by_title("Usage"):
            for line in usage.body:
                part_lens.append(len(line))
                line = target.escape_entities(line).replace(
                    target.escape_entities(item_name),
                    link
                )
                parts.append(line)
        out = []
        line = ""
        line_len = 0
        for part, part_len in zip(parts, part_lens):
            part = target.code_span(part)
            part = target.line_with_break(part)[0]
            if line_len + part_len > 80 or part_len > 40:
                if line:
                    line = target.quote(line)[0];
                    out.append(line)
                line = part
                line_len = part_len
            else:
                if line:
                    line += "&nbsp; &nbsp; "
                line += part
                line_len += part_len
        if line:
            line = target.quote(line)[0];
            out.extend(target.paragraph([line]))
        return out

    def get_file_lines(self, controller, target):
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
        children = self.sort_children(front_blocks, back_blocks)
        out = []
        out.extend(target.header(str(self), lev=target.ITEM))
        for child in children:
            out.extend(child.get_file_lines(controller, target))
        out.extend(target.horizontal_rule())
        return out


class ImageBlock(GenericBlock):
    def __init__(self, title, subtitle, body, origin, parent=None, meta="", use_apngs=False):
        super().__init__(title, subtitle, body, origin, parent=parent)
        fileblock = parent
        while fileblock.parent:
            fileblock = fileblock.parent

        self.meta = meta
        self.image_num = 0
        self.image_url = None
        self.image_url_rel = None
        self.image_req = None

        script_lines = []
        script_lines.extend(fileblock.includes)
        script_lines.extend(fileblock.common_code)
        for line in self.body:
            if line.strip().startswith("--"):
                script_lines.append(line.strip()[2:])
            else:
                script_lines.append(line)
        self.raw_script = script_lines

        san_name = re.sub(r'[^A-Za-z0-9_-]', r'', os.path.basename(parent.subtitle.strip().lower().replace(" ","-")))
        if use_apngs:
            file_ext = "png"
        elif "Spin" in self.meta or "Anim" in self.meta:
            file_ext = "gif"
        else:
            file_ext = "png"
        if self.title == "Figure":
            parent.figure_num += 1
            self.image_num = parent.figure_num
            if parent.title in ["File", "LibFile"]:
                proposed_name = "figure{}.{}".format(self.image_num, file_ext)
            elif parent.title in ["Section", "Subsection"]:
                proposed_name = "{}-{}_fig{}.{}".format(parent.title.lower(), san_name, self.image_num, file_ext)
            else:
                proposed_name = "{}_fig{}.{}".format(san_name, self.image_num, file_ext)
            self.title = "{} {}".format(self.title, self.image_num)
        else:
            parent.example_num += 1
            self.image_num = parent.example_num
            img_suffix = "_{}".format(self.image_num) if self.image_num > 1 else ""
            proposed_name = "{}{}.{}".format(san_name, img_suffix, file_ext)
            self.title = "{} {}".format(self.title, self.image_num)

        file_dir, file_name = os.path.split(fileblock.origin.file.strip())
        file_base = os.path.splitext(file_name)[0]
        self.image_url_rel = os.path.join("images", file_base, proposed_name)
        self.image_url = os.path.join(file_dir, self.image_url_rel)

    def generate_image(self, target):
        self.image_req = None
        if "NORENDER" in self.meta:
            return
        show_img = (
            any(x in self.meta for x in ("2D", "3D", "Spin", "Anim")) or
            self.parent.title in ("File", "LibFile", "Module", "Function&Module")
        )
        if show_img:
            outfile = os.path.join(target.docs_dir, self.image_url)
            outdir = os.path.dirname(outfile)
            os.makedirs(outdir, mode=0o744, exist_ok=True)

            self.image_req = image_manager.new_request(
                self.origin.file, self.origin.line,
                outfile, self.raw_script, self.meta,
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

    def get_file_lines(self, controller, target):
        fileblock = self.parent
        while fileblock.parent:
            fileblock = fileblock.parent
        out = []
        if "Hide" in self.meta:
            return out

        self.generate_image(target)

        code = []
        code.extend([line for line in fileblock.includes])
        code.extend([line for line in self.body if not line.strip().startswith("--")])

        do_render = "NORENDER" not in self.meta and (
                self.parent.title in ["Module", "Function&Module"] or
                any(tag in self.meta for tag in ["2D","3D","Spin","Anim"])
            )

        code_below = False
        width = ''
        height = ''
        if self.image_req:
            code_below = self.image_req.script_under
            width = int(self.image_req.imgsize[0])
            height = int(self.image_req.imgsize[1])
        sub = self.parse_links(self.subtitle, controller, target)
        sub = target.escape_entities(sub)
        if "Figure" in self.title:
            out.extend(target.image_block(self.parent.subtitle, self.title, sub, rel_url=self.image_url_rel, code_below=code_below, width=width, height=height))
        elif not do_render:
            out.extend(target.image_block(self.parent.subtitle, self.title, sub, code=code, code_below=code_below, width=width, height=height))
        else:
            out.extend(target.image_block(self.parent.subtitle, self.title, sub, code=code, rel_url=self.image_url_rel, code_below=code_below, width=width, height=height))
        return out


class FigureBlock(ImageBlock):
    def __init__(self, title, subtitle, body, origin, parent, meta="", use_apngs=False):
        super().__init__(title, subtitle, body, origin, parent=parent, meta=meta, use_apngs=use_apngs)


class ExampleBlock(ImageBlock):
    def __init__(self, title, subtitle, body, origin, parent, meta="", use_apngs=False):
        super().__init__(title, subtitle, body, origin, parent=parent, meta=meta, use_apngs=use_apngs)




# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
