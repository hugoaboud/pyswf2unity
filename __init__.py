import os
import shutil
import logging

from config import SWF_FILE, ANIM_TEMPLATE, TERMINAL_LOG_LEVEL
from swf_doc import SWFDocument
from svg import SVGDocument
from anim import AnimDocument
from config import ANIM_TEMPLATE

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
outFolder = '{}/{}2'.format(rootFolder,alias)+"5"
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

logger.setLevel(logging.INFO)
swf = SWFDocument("{}/{}".format(rootFolder, SWF_FILE), depthNames = {1:'tail',3:'hat',4:'ear'})
svg = SVGDocument(swf, False)
anim = AnimDocument(swf, svg)
svg.export(outFolder)
logger.setLevel(logging.DEBUG)
anim.export(rootFolder, outFolder)

quit()

SWF2Unity.do(swf,svg,anim)
