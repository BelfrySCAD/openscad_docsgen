from __future__ import print_function

from .target_githubwiki import Target_GitHubWiki
from .target_wiki import Target_Wiki
from .target_mkdocs import Target_MKDocs


default_target = "githubwiki"
target_classes = {
    "githubwiki": Target_GitHubWiki,
    "wiki": Target_Wiki,
    "mkdocs": Target_MKDocs,
}


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
