from swf.movie import SWF
from swf.export import SingleShapeSVGExporter
from io import BytesIO
import yaml
import numpy as np
from math import pi
import shutil
import logging
import os

##                  ##
#       CONFIG       #
##                  ##

SWF_FILE = 'monica_walk_legs.swf'
ANIM_TEMPLATE = 'templates/template.anim'
SCALE = 0.05
TERMINAL_LOG_LEVEL = logging.DEBUG

##                  ##
#       MODEL        #
##                  ##

class SWFShape:
    def __init__(self, id):
        self.id = id
    def __str__(self):
        return '[SHAPE|{}]'.format(self.id)

class SWFSprite:
    def __init__(self, id, shape):
        self.id = id
        self.shape = shape
        self.depth = -1
        self.matrix = None
    def __str__(self):
        return '[SPRITE|{}] (shape.id: {}, depth: {}, matrix: {})'.format(self.id, self.shape.id, self.depth, self.matrix)
    def name(self):
        return '[SPRITE|{}]'.format(self.id)

##                  ##
#       SETUP        #
##                  ##

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
out_folder = './{}'.format(alias)
logging.info('\t<directoy>\t"{}"'.format(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists(out_folder):
    shutil.rmtree(out_folder, ignore_errors=True)
os.makedirs(out_folder)

# Logfile
logfile = logging.FileHandler('./{}/conversion.log'.format(alias))
logfile.setLevel(logging.DEBUG)
logfile.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(logfile)
logging.info('\t<alias>\t\t"{}"'.format(alias))
logging.info('\t<logfile>\t"{}"'.format('./{}/conversion.log'.format(alias)))

##              ##
#       SWF      #
##              ##

# SVG (export mesh)
SVGExporter = SingleShapeSVGExporter()

# load and parse the SWF
logging.info("")
logging.info("<SWF> Starting parse...")
swf = SWF(open(SWF_FILE, 'rb'))
FRAME_RATE = swf.header.frame_rate
frame_count = swf.header.frame_count

logging.debug(swf)

# model data
shapes = list()
sprites = list()
keyframes = list()
keyframes.append(dict())

# matrix utils
def _translation(matrix):
    return [matrix[4]*SCALE,matrix[5]*SCALE]

def _scale(matrix):
    return [np.asscalar(np.linalg.norm([matrix[0],matrix[1]])),np.asscalar(np.linalg.norm([matrix[2],matrix[3]]))]

def _rotation(matrix):
    angle = np.asscalar(np.arctan2(matrix[0],matrix[1])*180/pi-90)
    return angle;

def _mult(a, b):
    matrix_a = np.matrix([[a[0],a[2],a[4]],[a[1],a[3],a[5]],[0,0,1]])
    matrix_b = np.matrix([[b[0],b[2],b[4]],[b[1],b[3],b[5]],[0,0,1]])
    mult = (matrix_a * matrix_b).tolist()
    return [mult[0][0],mult[1][0],mult[0][1],mult[1][1],mult[0][2],mult[1][2]]

logging.info("<SWF> Starting modeling...")

k = 0
lastDefinedShape = None
lastDefinedSprite = None
for tag in swf.tags:

    # [DefineShape]
    if (tag.type == 2):
        # Create shape model
        lastDefinedShape = SWFShape(tag.characterId)
        logging.info("<SWF> {} created".format(lastDefinedShape))
        shapes.append(lastDefinedShape)
        # Export shape as SVG file
        logging.info("<SVG> Exporting shape {} to {}/{}.svg".format(tag.characterId,out_folder,tag.characterId))
        open('./{}/{}.svg'.format(out_folder,tag.characterId), 'wb').write(SVGExporter.export_single_shape(tag, swf).read())

    # [DefineSprite]
    elif (tag.type == 39):
        lastDefinedSprite = SWFSprite(tag.characterId, lastDefinedShape)
        for tagtag in tag.tags:
            # [PlaceObejct2]
            if (tagtag.type == 26):
                lastDefinedSprite.matrix = tagtag.matrix.to_array()
                break
            print(tagtag)
        logging.info("<SWF> {} created".format(lastDefinedSprite))
        sprites.append(lastDefinedSprite)

    # [PlaceObject2]
    elif (tag.type == 26):
        # Find corresponding shape
        sprite = [s for s in sprites if s.depth == tag.depth]
        if (not len(sprite)):
            if (tag.hasCharacter):
                sprite = lastDefinedSprite
                sprite.depth = tag.depth
            else:
                logging.error("<SWF> Couldn't find Sprite {}".format(tag.characterId))
                continue
        else:
            sprite = sprite[0]

        # If this PlaceObject changes the depth of a character, update depth
        if (tag.hasCharacter):
            logging.debug("<SWF> Moving Sprite {} to depth {}".format(tag.characterId,tag.depth))
            lastDefinedShape.depth = tag.depth

        # Store matrix on current keyframe for sprite
        keyframes[k][sprite] = _mult(tag.matrix.to_array(),sprite.matrix);

    # [ShowFrame]
    elif (tag.type == 1 and k < frame_count):
        k += 1;
        keyframes.append(dict())

## Debug Output

logging.debug("<SWF> Shapes:")
for shape in shapes:
    logging.debug('\t{}'.format(shape))
logging.debug("<SWF> Sprites:")
for sprite in sprites:
    logging.debug('\t{}'.format(sprite))
logging.debug("<SWF> Keyframes:")
for k, keyframe in enumerate(keyframes[:-1]):
    logging.debug("\t[K|{}]".format(k))
    for sprite, matrix in keyframe.iteritems():
        logging.debug("\t\t{} : matrix {}".format(sprite.name(), matrix))

##        ##
#   ANIM   #
#   save   #
##        ##

logging.info("<ANIM> Parsing template file")
anim_template = open(ANIM_TEMPLATE, 'r')
try:
    anim = yaml.load(anim_template)
except yaml.YAMLError as exc:
    print(exc)

# Set template sample/frame rate
anim['AnimationClip']['m_Name'] = alias
anim['AnimationClip']['m_SampleRate'] = FRAME_RATE
anim['AnimationClip']['m_AnimationClipSettings']['m_StartTime'] = 0
anim['AnimationClip']['m_AnimationClipSettings']['m_StopTime'] = (len(keyframes)-1)/FRAME_RATE

logging.info("<ANIM> Writing header\n\t\tm_Name : {}\n\t\tm_SampleRate : {}\n\t\tm_StartTime : {}\n\t\tm_StopTime : {}".format(anim['AnimationClip']['m_Name'], FRAME_RATE, 0, (frame_count-1)/FRAME_RATE))

# Clear template
anim['AnimationClip']['m_EditorCurves'] = []
anim['AnimationClip']['m_PositionCurves'] = []
anim['AnimationClip']['m_ScaleCurves'] = []
anim['AnimationClip']['m_EulerCurves'] = []

logging.info("<ANIM> Creating curves...")

# Create curves for each registered shape
positionCurves = dict()
scaleCurves = dict()
rotationCurves = dict()
for sprite in sprites:
    # Position
    positionCurve = dict({'curve':dict()})
    positionCurve['curve']['serializedVersion'] = 2
    positionCurve['path'] = str(sprite.id)
    positionCurve['curve']['m_PreInfinity'] = 2
    positionCurve['curve']['m_PostInfinity'] = 2
    positionCurve['curve']['m_RotationOrder'] = 4
    positionCurve['curve']['m_Curve'] = list()
    positionCurves[sprite] = positionCurve
    # Scale
    scaleCurve = dict({'curve':dict()})
    scaleCurve['curve']['serializedVersion'] = 2
    scaleCurve['path'] = str(sprite.id)
    scaleCurve['curve']['m_PreInfinity'] = 2
    scaleCurve['curve']['m_PostInfinity'] = 2
    scaleCurve['curve']['m_RotationOrder'] = 4
    scaleCurve['curve']['m_Curve'] = list()
    scaleCurves[sprite] = scaleCurve
    # Rotation
    rotationCurve = dict({'curve':dict()})
    rotationCurve['curve']['serializedVersion'] = 2
    rotationCurve['path'] = str(sprite.id)
    rotationCurve['curve']['m_PreInfinity'] = 2
    rotationCurve['curve']['m_PostInfinity'] = 2
    rotationCurve['curve']['m_RotationOrder'] = 4
    rotationCurve['curve']['m_Curve'] = list()
    rotationCurves[sprite] = rotationCurve

logging.info("<ANIM> Populating curves...")

# Populate curves with keyframes
for i, keyframe in enumerate(keyframes):
    for id, matrix in keyframe.iteritems():
        # Position
        translation = _translation(matrix)
        positionKeyframe = dict()
        positionKeyframe['serializedVersion'] = 2
        positionKeyframe['time'] = i/FRAME_RATE
        positionKeyframe['value'] = dict({'x': translation[0], 'y': -translation[1], 'z': 0})
        positionKeyframe['inSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        positionKeyframe['outSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        positionKeyframe['tangentMode'] = 0
        positionCurves[id]['curve']['m_Curve'].append(positionKeyframe)
        # Scale
        scale = _scale(matrix)
        scaleKeyframe = dict()
        scaleKeyframe['serializedVersion'] = 2
        scaleKeyframe['time'] = i/FRAME_RATE
        scaleKeyframe['value'] = dict({'x': scale[0], 'y': scale[1], 'z': 0})
        scaleKeyframe['inSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        scaleKeyframe['outSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        scaleKeyframe['tangentMode'] = 0
        scaleCurves[id]['curve']['m_Curve'].append(scaleKeyframe)
        # Rotation
        rotation = _rotation(matrix)
        rotationKeyframe = dict()
        rotationKeyframe['serializedVersion'] = 2
        rotationKeyframe['time'] = i/FRAME_RATE
        rotationKeyframe['value'] = dict({'x': 0, 'y': 0, 'z': rotation})
        rotationKeyframe['inSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        rotationKeyframe['outSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        rotationKeyframe['tangentMode'] = 0
        rotationCurves[id]['curve']['m_Curve'].append(rotationKeyframe)

# Merge curves into template
logging.info("<ANIM> Merging PositionCurves into template")
for positionCurve in positionCurves.values():
    anim['AnimationClip']['m_PositionCurves'].append(positionCurve)

logging.info("<ANIM> Merging ScaleCurves into template")
for scaleCurve in scaleCurves.values():
    anim['AnimationClip']['m_ScaleCurves'].append(scaleCurve)

logging.info("<ANIM> Merging EulerCurves into template")
for rotationCurve in rotationCurves.values():
    anim['AnimationClip']['m_EulerCurves'].append(rotationCurve)

## Debug Output

logging.debug("<ANIM> Keyframes created:")
logging.debug("\tPosition:")
for curve in anim['AnimationClip']['m_PositionCurves']:
    logging.debug("\t\tpath: {}".format(curve['path']))
    for keyframe in curve['curve']['m_Curve']:
        logging.debug("\t\t{}".format(keyframe))
logging.debug("\tScale:")
for curve in anim['AnimationClip']['m_ScaleCurves']:
    logging.debug("\tpath: {}".format(curve['path']))
    for keyframe in curve['curve']['m_Curve']:
        logging.debug("\t\t{}".format(keyframe))
logging.debug("\tRotation:")
for curve in anim['AnimationClip']['m_EulerCurves']:
    logging.debug("\tpath: {}".format(curve['path']))
    for keyframe in curve['curve']['m_Curve']:
        logging.debug("\t\t{}".format(keyframe))

##                  ##
#       OUTPUT       #
##                  ##

logging.info("<ANIM> Exporting animation to {}/{}.anim".format(out_folder,alias))

anim_file = open('{}/{}.anim'.format(out_folder,alias), 'wb')
anim_file.write("""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!74 &7400000\n""")
anim_file.write(yaml.dump(anim))
