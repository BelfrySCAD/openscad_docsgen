from __future__ import print_function

import re

from .target_wiki import Target_Wiki


class Target_GitHubWiki(Target_Wiki):
    def __init__(self, project_name=None, docs_dir="docs"):
        super().__init__(project_name=project_name, docs_dir=docs_dir)

    def image_block(self, item_name, title, subtitle="", code=[], code_below=False, rel_url=None, width='', height=''):
        out = []
        out.extend(self.block_header(title, subtitle, escsub=False))
        if rel_url:
            out.extend(self.image(item_name, title, rel_url, width=width, height=height))
        if code_below:
            out.extend(self.markdown_block(['<br clear="all" />']))
        out.extend(self.code_block(code))
        if not code_below:
            out.extend(self.markdown_block(['<br clear="all" /><br/>']))
        return out

    def image(self, item_name, img_type="", rel_url="", height='', width=''):
        width = ' width="{}"'.format(width) if width else ''
        height = ' height="{}"'.format(height) if width else ''
        return [
            '<img align="left" alt="{0} {1}" src="{2}"{3}{4}>'.format(
                self.escape_entities(item_name),
                self.escape_entities(img_type),
                rel_url, width, height
            ),
            ""
        ]

    def code_block(self, code):
        out = []
        if code:
            out.extend(self.indent_lines(code))
            out.append("")
        return out



# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
