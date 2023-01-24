from __future__ import print_function

import re


class Target_Wiki(object):
    FILE = 1
    SECTION = 2
    SUBSECTION = 2
    ITEM = 3
    def __init__(self, project_name=None, docs_dir="docs"):
        self.docs_dir = docs_dir
        self.project_name = project_name

    def get_suffix(self):
        return ".md"

    def postprocess(self, lines):
        return lines

    def escape_entities(self, txt):
        """
        Escapes markdown symbols for underscores, ampersands, less-than and
        greater-than symbols.
        """
        out = ""
        quotpat = re.compile(r'([^`]*)(`[^`]*`)(.*$)')
        while txt:
            m = quotpat.match(txt)
            unquot  = m.group(1) if m else txt
            literal = m.group(2) if m else ""
            txt     = m.group(3) if m else ""
            unquot = unquot.replace(r'_', r'\_')
            unquot = unquot.replace(r'&', r'&amp;')
            unquot = unquot.replace(r'<', r'&lt;')
            unquot = unquot.replace(r'>', r'&gt;')
            out += unquot + literal
        return out

    def bold(self, txt):
        return "**{}**".format(txt)

    def italics(self, txt):
        return "*{}*".format(txt)

    def line_with_break(self, line):
        if isinstance(line,list):
            line[-1] += "  "
            return line
        return [line + "  "]

    def quote(self, lines=[]):
        if isinstance(lines,list):
            return [">" + line for line in lines]
        return [">" + lines]

    def paragraph(self, lines=[]):
        lines.append("")
        return lines

    def footnote_marks(self, footnotes):
        out = ""
        for mark, note, origin in footnotes:
            marks = ' <sup title="{1}">[{0}](#file-footnotes)</sup>'.format(mark, note)
            out = out + marks
        return out

    def header_link(self, name):
        """
        Generates markdown link for a header.
        """
        refpat = re.compile("[^a-z0-9_ -]")
        return refpat.sub("", name.lower()).replace(" ", "-")

    def indent_lines(self, lines):
        return [" "*4 + line for line in lines]

    def get_link(self, label, anchor="", file="", literalize=True):
        if literalize:
            label = "`{0}`".format(label)
        else:
            label = self.escape_entities(label)
        if anchor:
            anchor = "#" + anchor
        return "[{0}]({1}{2})".format(label, file, anchor)

    def code_span(self, txt):
        return "<code>{}</code>".format(txt)

    def horizontal_rule(self):
        return [ "---", "" ]

    def header(self, txt, lev=1, esc=True):
        return [
            "{} {}".format(
                "#" * lev,
                self.escape_entities(txt) if esc else txt
            ),
            ""
        ]

    def block_header(self, title, subtitle="", escsub=True):
        return [
            "**{}:** {}".format(
                self.escape_entities(title),
                self.escape_entities(subtitle) if escsub else subtitle
            ),
            ""
        ]

    def markdown_block(self, text=[]):
        out = text
        out.append("")
        return out

    def image_block(self, item_name, title, subtitle="", code=[], code_below=False, rel_url=None, **kwargs):
        out = []
        out.extend(self.block_header(title, subtitle))
        if not code_below:
            out.extend(self.code_block(code))
        if rel_url:
            out.extend(self.image(item_name, title, rel_url))
        if code_below:
            out.extend(self.code_block(code))
        return out

    def image(self, item_name, img_type="", rel_url="", **kwargs):
        return [
            '![{0} {1}]({2} "{0} {1}")'.format(
                self.escape_entities(item_name),
                self.escape_entities(img_type),
                rel_url
            ),
            ""
        ]

    def code_block(self, code):
        out = []
        if code:
            out.append("``` {.C linenos=True}")
            out.extend(code)
            out.append("```")
            out.append("")
        return out

    def bullet_list_start(self):
        return []

    def bullet_list_item(self, item):
        out = ["- {}".format(item)]
        return out

    def bullet_list_end(self):
        return [""]

    def bullet_list(self, items):
        out = self.bullet_list_start()
        for item in items:
            out.extend(self.bullet_list_item(self.escape_entities(item)))
        out.extend(self.bullet_list_end())
        return out

    def numbered_list_start(self):
        return []

    def numbered_list_item(self, num, item):
        out = [
            "{}. {}".format(num, item)
        ]
        return out

    def numbered_list_end(self):
        return [""]

    def numbered_list(self, items):
        out = self.numbered_list_start()
        for num, item in enumerate(items):
            out.extend(self.numbered_list_item(num+1, item))
        out.extend(self.numbered_list_end())
        return out

    def table(self, headers, rows):
        out = []
        hcells = []
        lcells = []
        for hdr in headers:
            if hdr.startswith("^"):
                hdr = hdr.lstrip("^")
            hcells.append(hdr)
            lcells.append("-"*min(20,len(hdr)))
        out.append(" | ".join(hcells))
        out.append(" | ".join(lcells))
        for row in rows:
            fcells = []
            for i, cell in enumerate(row):
                hdr = headers[i]
                if hdr.startswith("^"):
                    cell = " / ".join(
                        "{:20s}".format("`{}`".format(x.strip()))
                        for x in cell.split("/")
                    )
                fcells.append(cell)
            out.append( " | ".join(fcells) )
        out.append("")
        return out



# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
