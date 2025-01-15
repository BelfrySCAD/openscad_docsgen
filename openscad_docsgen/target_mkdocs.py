from __future__ import print_function

import re

from .target_wiki import Target_Wiki


class Target_MKDocs(Target_Wiki):

    @property
    def TOCFILE(self):
        return "index" + self.get_suffix()

    @property
    def TOPICFILE(self):
        return "topics" + self.get_suffix()

    @property
    def INDEXFILE(self):
        return "alphaindex" + self.get_suffix()

    @property
    def CHEATFILE(self):
        return "cheatsheet" + self.get_suffix()

    @property
    def SIDEBARFILE(self):
        return "_sidebar" + self.get_suffix()

    def get_link(self, label, anchor="", file="", literalize=True):
        if literalize:
            label = "`{0}`".format(label)
        else:
            label = self.escape_entities(label)
        if file:
            file += '.md'
        if anchor:
            anchor = "#" + anchor
        return "[{0}]({1}{2})".format(label, file, anchor)