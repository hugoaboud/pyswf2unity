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

SWF_FILE = 'tests/monica_walk_body.swf'
ANIM_TEMPLATE = 'templates/template.anim'
SCALE = 0.05
TERMINAL_LOG_LEVEL = logging.DEBUG

##                  ##
#       UTIL         #
##                  ##

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

##                  ##
#       MODEL        #
##                  ##

class SWFCharacter(object):
    def __init__(self, id):
        self.id = id
        self.depth = -1
    def name(self):
        return '[CHAR|{}]'.format(self.id)

class SWFShape(SWFCharacter):
    def __init__(self, id):
        self.display = False
        super(SWFShape, self).__init__(id)
    def __str__(self):
        return '[SHAPE|{}] display: {}'.format(self.id, self.display)
    def name(self):
        return '[SHAPE|{}]'.format(self.id)

class SWFSprite(SWFCharacter):
    def __init__(self, id, frameCount, shape):
        super(SWFSprite, self).__init__(id)
        self.frameCount = frameCount
        self.shape = shape
        self.matrix = None
    def __str__(self):
        return '[SPRITE|{}] (shape.id: {}, frameCount: {}, depth: {}, matrix: {})'.format(self.id, self.shape.id, self.frameCount, self.depth, self.matrix)
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
    shutil.rmtree(out_folder)
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

class SWFCharacter:
    @staticmethod
    def getById(id):
        shape = [s for s in shapes if s.id == tag.characterId]
        sprite = [s for s in sprites if s.id == tag.characterId]
        if (len(shape)): return shape[0]
        elif (len(sprite)): return sprite[0]
        else: return None
    @staticmethod
    def getByDepth(depth):
        shape = [s for s in shapes if s.depth == tag.depth]
        sprite = [s for s in sprites if s.depth == tag.depth]
        if (len(shape)): return shape[0]
        elif (len(sprite)): return sprite[0]
        else: return None

logging.info("<SWF> Starting modeling...")

k = 0
lastDefinedShape = None
lastDefinedSprite = None
for tag in swf.tags:

    # [DefineShape], [DefineShape2], [DefineShape3], [DefineShape4]
    if (tag.type == 2 or tag.type == 22 or tag.type == 32 or tag.type == 83):
        # Create shape model
        lastDefinedShape = SWFShape(tag.characterId)
        logging.info("<SWF> {} created".format(lastDefinedShape))
        shapes.append(lastDefinedShape)
        # Export shape as SVG file
        logging.info("<SVG> Exporting shape {} to {}/{}.svg".format(tag.characterId,out_folder,tag.characterId))
        open('./{}/{}.svg'.format(out_folder,tag.characterId), 'wb').write(SVGExporter.export_single_shape(tag, swf).read())

    # [DefineSprite]
    elif (tag.type == 39):
        lastDefinedSprite = SWFSprite(tag.characterId, tag.frameCount, lastDefinedShape)
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

        # Find character associated to this depth
        character = SWFCharacter.getByDepth(tag.depth)

        if (tag.hasCharacter):
            # If another character is in this depth, remove it and refer to the new
            if (character != None and character.characterId != tag.characterId):
                logging.debug("<SWF> Removing Character {} from depth {}".format(character.characterId,tag.depth))
                character.depth = -1
            # Find new character and set depth
            character = SWFCharacter.getById(tag.characterId)
            if (character != None):
                logging.debug("<SWF> Moving Character {} to depth {}".format(tag.characterId,tag.depth))
                character.depth = tag.depth
            else:
                logging.error("<SWF> Couldn't find Character {}".format(tag.characterId))

        # Store matrix on current keyframe for character
        if (type(character) == SWFSprite):
            keyframes[k][character] = _mult(tag.matrix.to_array(),character.matrix)
        elif (type(character) == SWFShape):
            character.display = True
            keyframes[k][character] = tag.matrix.to_array()

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
    for character, matrix in keyframe.iteritems():
        logging.debug("\t\t{} : matrix {}".format(character.name(), matrix))

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

animCharacters = sprites + [s for s in shapes if s.display]

logging.info("<ANIM> Creating curves...")

# Create curves for each registered shape
positionCurves = dict()
scaleCurves = dict()
rotationCurves = dict()
for character in animCharacters:
    # Position
    positionCurve = dict({'curve':dict()})
    positionCurve['curve']['serializedVersion'] = 2
    positionCurve['path'] = str(character.id)
    positionCurve['curve']['m_PreInfinity'] = 2
    positionCurve['curve']['m_PostInfinity'] = 2
    positionCurve['curve']['m_RotationOrder'] = 4
    positionCurve['curve']['m_Curve'] = list()
    positionCurves[character] = positionCurve
    # Scale
    scaleCurve = dict({'curve':dict()})
    scaleCurve['curve']['serializedVersion'] = 2
    scaleCurve['path'] = str(character.id)
    scaleCurve['curve']['m_PreInfinity'] = 2
    scaleCurve['curve']['m_PostInfinity'] = 2
    scaleCurve['curve']['m_RotationOrder'] = 4
    scaleCurve['curve']['m_Curve'] = list()
    scaleCurves[character] = scaleCurve
    # Rotation
    rotationCurve = dict({'curve':dict()})
    rotationCurve['curve']['serializedVersion'] = 2
    rotationCurve['path'] = str(character.id)
    rotationCurve['curve']['m_PreInfinity'] = 2
    rotationCurve['curve']['m_PostInfinity'] = 2
    rotationCurve['curve']['m_RotationOrder'] = 4
    rotationCurve['curve']['m_Curve'] = list()
    rotationCurves[character] = rotationCurve

logging.info("<ANIM> Populating curves...")

# Populate curves with keyframes
for i, keyframe in enumerate(keyframes):
    for character, matrix in keyframe.iteritems():
        # Position
        translation = _translation(matrix)
        positionKeyframe = dict()
        positionKeyframe['serializedVersion'] = 2
        positionKeyframe['time'] = i/FRAME_RATE
        positionKeyframe['value'] = dict({'x': translation[0], 'y': -translation[1], 'z': 0})
        positionKeyframe['inSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        positionKeyframe['outSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        positionKeyframe['tangentMode'] = 0
        positionCurves[character]['curve']['m_Curve'].append(positionKeyframe)
        # Scale
        scale = _scale(matrix)
        scaleKeyframe = dict()
        scaleKeyframe['serializedVersion'] = 2
        scaleKeyframe['time'] = i/FRAME_RATE
        scaleKeyframe['value'] = dict({'x': scale[0], 'y': scale[1], 'z': 0})
        scaleKeyframe['inSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        scaleKeyframe['outSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        scaleKeyframe['tangentMode'] = 0
        scaleCurves[character]['curve']['m_Curve'].append(scaleKeyframe)
        # Rotation
        rotation = _rotation(matrix)
        rotationKeyframe = dict()
        rotationKeyframe['serializedVersion'] = 2
        rotationKeyframe['time'] = i/FRAME_RATE
        rotationKeyframe['value'] = dict({'x': 0, 'y': 0, 'z': rotation})
        rotationKeyframe['inSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        rotationKeyframe['outSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        rotationKeyframe['tangentMode'] = 0
        rotationCurves[character]['curve']['m_Curve'].append(rotationKeyframe)

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

logging.info("<ANIM> Exporting animation to {}/{}.anim".format(out_folder,alias.split('/')[-1]))

anim_file = open('{}/{}.anim'.format(out_folder,alias.split('/')[-1]), 'wb')
anim_file.write("""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!74 &7400000\n""")
anim_file.write(yaml.dump(anim))
