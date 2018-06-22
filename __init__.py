import os
import shutil
import logging

from config import SWF_FILE, ANIM_TEMPLATE, TERMINAL_LOG_LEVEL
from swf_doc import SWFDocument
from svg import SVGDocument
from anim import AnimDocument
from config import ANIM_TEMPLATE, DEPTH_NAMES

# Logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logstream = logging.StreamHandler()
logstream.setLevel(TERMINAL_LOG_LEVEL)
logstream.setFormatter(logging.Formatter('%(levelname)s\t%(message)s'))
logger.addHandler(logstream)
logging.info("")

# Output Folder
alias = SWF_FILE.split('.')[0];
rootFolder = os.path.dirname(os.path.abspath(__file__))
outFolder = '{}/{}'.format(rootFolder,alias)
logging.info('\t<root folder>\t"{}"'.format(rootFolder))
logging.info('\t<output folder>\t"{}"'.format(outFolder))
if os.path.exists(outFolder):
    shutil.rmtree(outFolder)
os.makedirs(outFolder)

# Logfile
logfile = logging.FileHandler('{}/{}/conversion.log'.format(rootFolder, alias))
logfile.setLevel(logging.DEBUG)
logfile.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(logfile)
logging.info('\t<alias>\t\t"{}"'.format(alias))
logging.info('\t<logfile>\t"{}"'.format('{}/{}/conversion.log'.format(rootFolder, alias)))

##              ##
#      MAIN      #
##              ##

logging.info("")

logger.setLevel(logging.DEBUG)
swf = SWFDocument("{}/{}".format(rootFolder, SWF_FILE))
svg = SVGDocument(swf)
logger.setLevel(logging.DEBUG)
anim = AnimDocument(swf, svg)
svg.export(outFolder)
anim.export(rootFolder, outFolder)
quit()

quit()
