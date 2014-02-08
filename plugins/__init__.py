from glob import glob
#from keyword import iskeyword
import keyword
import re
from os.path import dirname, join, split, splitext

def isidentifier(s):
    if s in keyword.kwlist:
        return False
    return re.match(r'^[a-z_][a-z0-9_]*$', s, re.I) is not None

basedir = dirname(__file__)

__all__ = []
for name in glob(join(basedir, '*.py')):
    module = splitext(split(name)[-1])[0]
    print "module = ", module
#    if not module.startswith('_') and module.isidentifier() and not iskeyword(module):
    if not module.startswith('_') and isidentifier(module) and not keyword.iskeyword(module):
        try:
            __import__(__name__+'.'+module)
        except:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning('Ignoring exception while loading the %r plug-in.', module)
        else:
            __all__.append(module)
__all__.sort()
