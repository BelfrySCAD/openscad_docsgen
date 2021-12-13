from __future__ import print_function

from .target_githubwiki import Target_GitHubWiki
from .target_wiki import Target_Wiki


default_target = "githubwiki"
target_classes = {
    "githubwiki": Target_GitHubWiki,
    "wiki": Target_Wiki,
}


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
