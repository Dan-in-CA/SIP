from glob import glob
from keyword import iskeyword
from os.path import dirname, join, split, splitext

basedir = dirname(__file__)

__all__ = []
for name in glob(join(basedir, '*.py')):
    module = splitext(split(name)[-1])[0]
    if not module.startswith('_') and module.isidentifier() and not iskeyword(module):
        try:
            __import__(__name__+'.'+module)
        except:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning('Ignoring exception while loading the %r plug-in.', module)
        else:
            __all__.append(module)
__all__.sort()
