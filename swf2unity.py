from swf.movie import SWF
from swf.tag import TagShowFrame, TagPlaceObject, TagRemoveObject
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

SWF_FILE = 'tests/elefanto1_2.swf'
ANIM_TEMPLATE = 'templates/template.anim'
SCALE = 0.05
TERMINAL_LOG_LEVEL = logging.DEBUG

##                  ##
#       UTIL         #
##                  ##

def _mult(a, b):
    matrix_a = np.matrix([[a[0],a[2],a[4]],[a[1],a[3],a[5]],[0,0,1]])
    matrix_b = np.matrix([[b[0],b[2],b[4]],[b[1],b[3],b[5]],[0,0,1]])
    mult = (matrix_a * matrix_b).tolist()
    return [mult[0][0],mult[1][0],mult[0][1],mult[1][1],mult[0][2],mult[1][2]]

##                  ##
#       MODEL        #
##                  ##

class SWFCharacter(object):
    def __init__(self, tag):
        self.id = tag.characterId
        self.depth = -1
    def name(self):
        return '[CHAR|{}]'.format(self.id)

class SWFShape(SWFCharacter):
    def __init__(self, tag):
        self.bounds = tag.shape_bounds
        super(SWFShape, self).__init__(tag)
    def __str__(self):
        return '[SHAPE|{}] centerMatrix: {}'.format(self.id, self.getCenterMatrix())
    def name(self):
        return '[SHAPE|{}]'.format(self.id)
    def getCenterMatrix(self):
        return [1,0,0,1,self.bounds.xmin+(self.bounds.xmax-self.bounds.xmin)/2,self.bounds.ymin+(self.bounds.ymax-self.bounds.ymin)/2]

class SWFMorphShape(SWFShape):
    def __init__(self, tag):
        self.ratio = 0
        tag.shape_bounds = tag.startBounds
        super(SWFMorphShape, self).__init__(tag)
    def __str__(self):
        return '[MORPH|{}] centerMatrix: {}'.format(self.id, self.getCenterMatrix())
    def name(self):
        return '[MORPH|{}]'.format(self.id)

class SWFSprite(SWFCharacter):
    def __init__(self, tag, shape):
        super(SWFSprite, self).__init__(tag)
        self.frameCount = tag.frameCount
        self.shape = shape
        self.matrix = None
    def __str__(self):
        return '[SPRITE|{}] (shape.id: {}, frameCount: {}, depth: {}, matrix: {})'.format(self.id, self.shape.id, self.frameCount, self.depth, self.matrix)
    def name(self):
        return '[SPRITE|{}]'.format(self.id)

class Keyframe(object):
    def __init__(self, f, character, matrix, depth):
        self.f = f
        self.character = character
        self.matrix = matrix
        self.depth = depth
    def dumpAnim(self):
        dump = dict()
        dump['serializedVersion'] = 2
        dump['time'] = self.f/FRAME_RATE
        dump['value'] = dict({'x': 0, 'y': 0, 'z': 0})
        dump['inSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        dump['outSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
        dump['tangentMode'] = 0
        return dump
    def getPositionKeyframe(self):
        position = self.getPosition()
        if (position == None): return None
        keyframe = self.dumpAnim()
        keyframe['value']['x'] = position[0]
        keyframe['value']['y'] = position[1]
        return keyframe
    def getScaleKeyframe(self):
        scale = self.getScale()
        if (scale == None): return None
        keyframe = self.dumpAnim()
        keyframe['value']['x'] = scale[0]
        keyframe['value']['y'] = scale[1]
        return keyframe
    def getEulerKeyframe(self):
        euler = self.getEuler()
        if (euler == None): return None
        keyframe = self.dumpAnim()
        keyframe['value']['z'] = euler
        return keyframe
    def getActiveKeyframe(self):
        keyframe = self.dumpAnim()
        keyframe['value'] = 1.0 if self.depth >= 0 else 0.0
        return keyframe
    def getPosition(self):
        if (self.matrix == None): return None
        return [self.matrix[4]*SCALE,self.matrix[5]*SCALE]
    def getScale(self):
        if (self.matrix == None): return None
        return [np.asscalar(np.linalg.norm([self.matrix[0],self.matrix[1]])),np.asscalar(np.linalg.norm([self.matrix[2],self.matrix[3]]))]
    def getEuler(self):
        if (self.matrix == None): return None
        euler = np.asscalar(np.arctan2(self.matrix[0],self.matrix[1])*180/pi-90)
        return euler;

class Curve(object):
    class Type:
        POSITION = 0,
        SCALE = 1,
        EULER = 2,
        ACTIVE = 3
    def __init__(self, type, character):
        self.character = character
        self.type = type
        self.keyframes = list()
    def dumpAnim(self):
        dump = dict({'curve':dict()})
        dump['curve']['serializedVersion'] = 2
        dump['path'] = str(self.character.id)
        dump['curve']['m_PreInfinity'] = 2
        dump['curve']['m_PostInfinity'] = 2
        dump['curve']['m_RotationOrder'] = 4
        dump['curve']['m_Curve'] = self.keyframes
        if (self.type == Curve.Type.ACTIVE):
            dump['attribute'] = 'm_IsActive'
            dump['classID'] = 1
            dump['script'] = dict({'fileID':0})
        return dump
    def addKeyframe(self, keyframe):
        #replace duplicates
        for k, key in enumerate(self.keyframes):
            if (key['time'] == keyframe['time']):
                self.keyframes[k]['value'] = keyframe['time']
        self.keyframes.append(keyframe)
    def cleanup(self):
        # insert default activeKeyframes on time 0 if the first keyframe
        # on the timeline is not at time 0
        # TODO: extend to every floatKeyframe
        if (self.type == Curve.Type.ACTIVE):
            if (len(self.keyframes) and self.keyframes[0]['time'] > 0):
                self.keyframes.insert(0,Keyframe(0,self.character,None,-1).getActiveKeyframe())

        # find and remove repeated keyframes
        for k, keyframe in enumerate(self.keyframes[0:]):
            if (keyframe['value'] == self.keyframes[k-1]['value']):
                keyframe['repeated'] = True

        for k, keyframe in enumerate(self.keyframes):
            if ("repeated" in keyframe):
                if (k < len(self.keyframes)-1):
                    if ("repeated" in self.keyframes[k+1]):
                        keyframe['delete'] = True
                del(keyframe['repeated'])
        self.keyframes = [keyframe for keyframe in self.keyframes if not ("delete" in keyframe)]

class Timeline(object):
    def __init__(self, frameCount):
        self.frameCount = frameCount
        self.frames = list()
        for _ in range(frameCount):
            self.frames.append(list())
        self.curves = list()
    def addKeyframe(self, keyframe):
        self.frames[keyframe.f].append(keyframe)
    def addCurveKeyframe(self, f, character, type, keyframe):
        curve = [c for c in self.curves if (c.character == character and c.type == type)]
        if not(len(curve)):
            logging.error("<ANIM> No curve found for character {} with type {}".format(character.name(), type))
            return
        curve = curve[0]
        curve.addKeyframe(keyframe)
    def getKeyframes(self, f):
        return self.frames[f]
    def getStartTime(self):
            return 0
    def getStopTime(self):
            return (self.frameCount-1)/FRAME_RATE

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
#       SVG      #
##              ##

class SingleShapeFrameSVGExporter(SingleShapeSVGExporter):

    def export_single_shape(self, shape_tag, swf, frame):
        self.frame = frame
        return super(SingleShapeFrameSVGExporter, self).export_single_shape(shape_tag, swf)

    def get_display_tags(self, tags, z_sorted=True):
        current_frame = 0
        frame_tags = dict() # keys are depths, values are placeobject tags
        for tag in tags:
            if isinstance(tag, TagShowFrame):
                if current_frame == self.frame:
                    break
                current_frame += 1
            elif isinstance(tag, TagPlaceObject):
                if current_frame == self.frame:
                    frame_tags[tag.depth] = tag

            elif isinstance(tag, TagRemoveObject):
                del frame_tags[tag.depth]

        return super(SingleShapeFrameSVGExporter, self).get_display_tags(tags, z_sorted)
        return super(SingleShapeFrameSVGExporter, self).get_display_tags(frame_tags.values(), z_sorted)

# SVG (export mesh)
SVGExporter = SingleShapeFrameSVGExporter()

##              ##
#       SWF      #
##              ##

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
timeline = Timeline(frame_count)

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

f = 0
lastDefinedShape = None
lastDefinedSprite = None
for tag in swf.tags:

    # [DefineShape], [DefineShape2], [DefineShape3], [DefineShape4]
    if (tag.type == 2 or tag.type == 22 or tag.type == 32 or tag.type == 83):
        # Create shape model
        lastDefinedShape = SWFShape(tag)
        logging.info("<SWF> {} created".format(lastDefinedShape))
        shapes.append(lastDefinedShape)
        # Export shape as SVG file
        logging.info("<SVG> Exporting shape {} to {}/{}.svg".format(tag.characterId,out_folder,tag.characterId))
        open('./{}/{}.svg'.format(out_folder,tag.characterId), 'wb').write(SVGExporter.export_single_shape(tag, swf, 0).read())

    # [DefineSprite]
    elif (tag.type == 39):
        lastDefinedSprite = SWFSprite(lastDefinedShape)
        for tagtag in tag.tags:
            # [PlaceObejct2]
            if (tagtag.type == 26):
                lastDefinedSprite.matrix = tagtag.matrix.to_array()
                break
            print(tagtag)
        logging.info("<SWF> {} created".format(lastDefinedSprite))
        sprites.append(lastDefinedSprite)

    # [DefineMorphShape]
    elif tag.type == 46:
        lastDefinedShape = SWFMorphShape(tag)
        logging.info("<SWF> {} created".format(lastDefinedShape))
        shapes.append(lastDefinedShape)
        # Export morph shape as SVG file
        logging.info("<SVG> Exporting morph shape {} to {}/{}.svg".format(tag.characterId,out_folder,tag.characterId))
        open('./{}/{}.svg'.format(out_folder,tag.characterId), 'wb').write(SVGExporter.export_single_shape(tag, swf, 0).read())

    # [PlaceObject2]
    elif (tag.type == 26):

        # Find character associated to this depth
        character = SWFCharacter.getByDepth(tag.depth)

        if (tag.hasCharacter):
            # If another character is in this depth, remove it and refer to the new
            if (character != None and character.id != tag.characterId):
                logging.debug("<SWF> Removing [CHAR|{}] from depth {}".format(character.id,tag.depth))
                character.depth = -1
                timeline.addKeyframe(Keyframe(f, character, None, -1))
            # Find new character and set depth
            character = SWFCharacter.getById(tag.characterId)
            if (character != None):
                logging.debug("<SWF> Moving [CHAR|{}] to depth {}".format(tag.characterId,tag.depth))
                character.depth = tag.depth
            else:
                logging.error("<SWF> Couldn't find [CHAR|{}]".format(tag.characterId))
                continue

        matrix = None
        if tag.hasMatrix:
            matrix =  tag.matrix.to_array()
        elif tag.hasCharacter:
            matrix = [1,0,0,1,0,0]
        if matrix != None:
            if (isinstance(character,SWFSprite)): matrix = _mult(matrix,character.matrix)
            elif (isinstance(character,SWFShape)): matrix = _mult(matrix,character.getCenterMatrix())

        logging.debug("<SWF> f{} [CHAR|{}] matrix: {}, depth: {}".format(f, tag.characterId, matrix, tag.depth))
        timeline.addKeyframe(Keyframe(f, character, matrix, tag.depth))

    # [ShowFrame]
    elif (tag.type == 1 and f < frame_count):
        logging.debug("<SWF> Show frame: {}".format(f))
        f += 1;

## Debug Output

logging.debug("<SWF> Shapes:")
for shape in shapes:
    logging.debug('\t{}'.format(shape))
logging.debug("<SWF> Sprites:")
for sprite in sprites:
    logging.debug('\t{}'.format(sprite))
logging.debug("<SWF> Keyframes:")
for f, frame in enumerate(timeline.frames):
    logging.debug("\t[frame{}]".format(f))
    for k, keyframe in enumerate(frame):
        logging.debug("\t\t[key{}] : character {} : matrix {} : depth {}".format(k, keyframe.character.name(), keyframe.matrix, keyframe.depth))

##        ##
#   ANIM   #
#   save   #
##        ##

logging.info("<ANIM> Parsing template file {}".format(ANIM_TEMPLATE))
anim_template = open(ANIM_TEMPLATE, 'r')
try:
    anim = yaml.load(anim_template)
except yaml.YAMLError as exc:
    logging.error(exc)

# Set template sample/frame rate
anim['AnimationClip']['m_Name'] = alias
anim['AnimationClip']['m_SampleRate'] = FRAME_RATE
anim['AnimationClip']['m_AnimationClipSettings']['m_StartTime'] = timeline.getStartTime()
anim['AnimationClip']['m_AnimationClipSettings']['m_StopTime'] = timeline.getStopTime()

logging.info("<ANIM> Writing header\n\t\tm_Name : {}\n\t\tm_SampleRate : {}\n\t\tm_StartTime : {}\n\t\tm_StopTime : {}".format(anim['AnimationClip']['m_Name'], FRAME_RATE, 0, (frame_count-1)/FRAME_RATE))

# Clear template
anim['AnimationClip']['m_EditorCurves'] = []
anim['AnimationClip']['m_PositionCurves'] = []
anim['AnimationClip']['m_ScaleCurves'] = []
anim['AnimationClip']['m_EulerCurves'] = []

logging.info("<ANIM> Creating curves...")

# Create curves for each registered shape
animCharacters = sprites + shapes
for character in animCharacters:
    timeline.curves.append(Curve(Curve.Type.POSITION, character))
    timeline.curves.append(Curve(Curve.Type.SCALE, character))
    timeline.curves.append(Curve(Curve.Type.EULER, character))
    timeline.curves.append(Curve(Curve.Type.ACTIVE, character))

print(timeline.curves)
logging.info("<ANIM> Populating curves...")

# Populate curves with keyframes
for f, frame in enumerate(timeline.frames):
    for k, keyframe in enumerate(frame):
        # Position
        positionKeyframe = keyframe.getPositionKeyframe()
        if (positionKeyframe != None):
            timeline.addCurveKeyframe(f, keyframe.character, Curve.Type.POSITION, positionKeyframe)
        # Scale
        scaleKeyframe = keyframe.getScaleKeyframe()
        if (scaleKeyframe != None):
            timeline.addCurveKeyframe(f, keyframe.character, Curve.Type.SCALE, scaleKeyframe)
        # Euler (rotation)
        eulerKeyframe = keyframe.getEulerKeyframe()
        if (eulerKeyframe != None):
            timeline.addCurveKeyframe(f, keyframe.character, Curve.Type.EULER, eulerKeyframe)
        # Active keyframe
        activeKeyframe = keyframe.getActiveKeyframe()
        if (activeKeyframe != None):
            timeline.addCurveKeyframe(f, keyframe.character, Curve.Type.ACTIVE, activeKeyframe)

# Merge curves into template
for curve in timeline.curves:
    curve.cleanup()
    type = ''
    tag = ''
    if (curve.type == Curve.Type.POSITION):
        type = 'PositionCurve'
        tag = 'm_PositionCurves'
    elif (curve.type == Curve.Type.SCALE):
        type = 'ScaleCurve'
        tag = 'm_ScaleCurves'
    elif (curve.type == Curve.Type.EULER):
        type = 'EulerCurve'
        tag = 'm_EulerCurves'
    elif (curve.type == Curve.Type.ACTIVE):
        type = 'ActiveCurve'
        tag = 'm_FloatCurves'
        print(curve.keyframes)

    logging.info('<ANIM> Merging {}|{} into template'.format(type, curve.character.id))
    anim['AnimationClip'][tag].append(curve.dumpAnim())


## Debug Output

logging.debug('<ANIM> Keyframes created:')
logging.debug('\tPosition:')
for curve in anim['AnimationClip']['m_PositionCurves']:
    logging.debug('\t\tpath: {}'.format(curve['path']))
    for keyframe in curve['curve']['m_Curve']:
        logging.debug('\t\t{}'.format(keyframe))
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
logging.debug("\Float:")
for curve in anim['AnimationClip']['m_FloatCurves']:
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
