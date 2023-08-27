# `name` is the name of the package as used for `pip install package`
name = "pygaposa"
# `path` is the name of the package for `import package`
path = name.lower().replace("-", "_").replace(" ", "_")
# Your version number should follow https://python.org/dev/peps/pep-0440 and
# https://semver.org
version = "0.1.dev0"
author = "Mark Watson"
author_email = "markwatson@cantab.net"
description = "Python model for access to Gaposa morotized shades API"
url = "https://github.com/mwatson2/pygaposa"
license = "MIT"