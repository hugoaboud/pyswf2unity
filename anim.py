import logging
import yaml

from config import ANIM_TEMPLATE, FRAMEKEYFRAME
from model import AnimType
from swf_doc import SWFDocument

class AnimDocument(object):

    class Type:
        SINGLE_SVG = 0
        MULTI_SVG = 1

    class Curve(object):
        def __init__(self, type, object):
            self.type = type
            self.object = object
            self.keyframes = list()
            self.timeline = None
        def dump(self):
            dump = dict({'curve':dict()})
            dump['curve']['serializedVersion'] = 2
            dump['path'] = str(self.object.name)
            dump['curve']['m_PreInfinity'] = 2
            dump['curve']['m_PostInfinity'] = 2
            dump['curve']['m_RotationOrder'] = 4
            dump['curve']['m_Curve'] = [k.dump() for k in self.keyframes]
            if (self.type == AnimType.ISACTIVE):
                dump['attribute'] = 'm_IsActive'
                dump['classID'] = 1
                dump['script'] = dict({'fileID':0})
            elif (self.type == AnimType.FRAME):
                dump['attribute'] = FRAMEKEYFRAME.ATTRIBUTE
                dump['classID'] = 114
                dump['script'] = dict({'fileID':11500000, 'guid':FRAMEKEYFRAME.GUID, 'type':3})
            return dump

        def addKeyframe(self, keyframe):
            #replace keyframes of the same type on the same time
            for k, key in enumerate(self.keyframes):
                if (type(key) == type(keyframe) and key.time == keyframe.time):
                    self.keyframes[k].set(keyframe)
                    return
            self.keyframes.append(keyframe)

        def hasKeyframes(self):
            return len(self.keyframes) > 0

        def optimize(self):
            # insert default keyframes on time 0 if the first keyframe
            # on the timeline is not at time 0 and is not zero
            if (len(self.keyframes)):
                first = self.keyframes[0]
                if (first.time > 0):
                    if (self.type == AnimType.ISACTIVE and first.active != 0):
                        default = IsActiveKeyframe(0,0).set(first)
                        self.keyframes.insert(0,default)

            # find and remove repeated keyframes
            repeated = []
            for k, keyframe in enumerate(self.keyframes[1:]):
                if keyframe.equals(self.keyframes[k]):
                    repeated.append(keyframe)
            todelete = []
            for k, keyframe in enumerate(self.keyframes):
                if keyframe in repeated:
                    if (k < len(self.keyframes)-1):
                        if self.keyframes[k+1] in repeated:
                            todelete.append(keyframe)
            self.keyframes = [k for k in self.keyframes if k not in todelete]

            # if two keyframes only and they're equal, remove the last
            if len(self.keyframes) == 2:
                if self.keyframes[0].equals(self.keyframes[1]):
                    del(self.keyframes[1])

            # if one keyframe only and it's default remove it
            if len(self.keyframes) == 1:
                if (self.keyframes[0].default()):
                    del(self.keyframes[0])

        def __str__(self):
            return "[{}|{}]".format(self.object.name, AnimType.Name(self.type))

    class Keyframe (object):
        def __init__(self, time, discrete = False):
            self.time = time
            self.discrete = discrete
        def dump(self):
            dump = dict()
            dump['serializedVersion'] = 2
            dump['time'] = self.time
            dump['value'] = dict({'x': 0, 'y': 0, 'z': 0})
            if (self.discrete):
                dump['inSlope'] = dict({'x': 'Infinity', 'y': 'Infinity', 'z': 'Infinity'})
                dump['outSlope'] = dict({'x': 'Infinity', 'y': 'Infinity', 'z': 'Infinity'})
                dump['tangentMode'] = 103
            else:
                dump['inSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
                dump['outSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
                dump['tangentMode'] = 0
            return dump
        def set(self, keyframe):
            keyframe.time = self.time
            return self
        def __str__(self):
            return "[Keyframe|{}]".format(self.time)
        def equals(self, other):
            return False
        def default(self):
            return None

    class PositionKeyframe(Keyframe):
        def __init__(self, time, transform, discrete = False):
            assert hasattr(transform, 'matrix') and transform.matrix != None
            self.position = transform.matrix.getPosition()
            super(AnimDocument.PositionKeyframe, self).__init__(time, discrete)
        def dump(self):
            dump = super(AnimDocument.PositionKeyframe, self).dump()
            dump['value']['x'] = self.position[0]
            dump['value']['y'] = -self.position[1]
            return dump
        def set(self, keyframe):
            dump = super(AnimDocument.PositionKeyframe, self).set(keyframe)
            self.position = keyframe.position
            return self
        def __str__(self):
            return "[PositionKeyframe|{:.3f}] {}".format(self.time, self.position)
        def equals(self, other):
            return self.position == other.position
        def default(self):
            return self.position == [0,0]

    class ScaleKeyframe(Keyframe):
        def __init__(self, time, transform, discrete = False):
            assert hasattr(transform, 'matrix') and transform.matrix != None
            self.scale = transform.matrix.getScale()
            super(AnimDocument.ScaleKeyframe, self).__init__(time, discrete)
        def dump(self):
            dump = super(AnimDocument.ScaleKeyframe, self).dump()
            dump['value']['x'] = self.scale[0]
            dump['value']['y'] = self.scale[1]
            return dump
        def set(self, keyframe):
            dump = super(AnimDocument.ScaleKeyframe, self).set(keyframe)
            self.scale = keyframe.scale
            return self
        def __str__(self):
            return "[ScaleKeyframe|{:.3f}] {}".format(self.time, self.scale)
        def equals(self, other):
            return self.scale == other.scale
        def default(self):
            return self.scale == [1,1]

    class EulerKeyframe(Keyframe):
        def __init__(self, time, transform, discrete = False):
            assert hasattr(transform, 'matrix') and transform.matrix != None
            self.euler = transform.matrix.getEuler()
            super(AnimDocument.EulerKeyframe, self).__init__(time, discrete)
        def dump(self):
            dump = super(AnimDocument.EulerKeyframe, self).dump()
            dump['value']['z'] = self.euler
            return dump
        def set(self, keyframe):
            dump = super(AnimDocument.EulerKeyframe, self).set(keyframe)
            self.euler = keyframe.euler
            return self
        def __str__(self):
            return "[EulerKeyframe|{:.3f}] {}".format(self.time, self.euler)
        def equals(self, other):
            return self.euler == other.euler
        def default(self):
            return self.euler == 0

    class IsActiveKeyframe(Keyframe):
        def __init__(self, time, transform, discrete = True):
            super(AnimDocument.IsActiveKeyframe, self).__init__(time, True)
            self.active = 1.0 if transform.char != None else 0.0
        def dump(self):
            dump = super(AnimDocument.IsActiveKeyframe, self).dump()
            dump['value'] = self.active
            dump['inSlope'] = 'Infinity'
            dump['outSlope'] = 'Infinity'
            return dump
        def set(self, keyframe):
            dump = super(AnimDocument.IsActiveKeyframe, self).set(keyframe)
            self.active = keyframe.active
            return self
        def __str__(self):
            return "[IsActiveKeyframe|{:.3f}] {}".format(self.time, self.active)
        def equals(self, other):
            return self.active == other.active
        def default(self):
            return self.active == 1.0

    class FrameKeyframe(Keyframe):
        def __init__(self, time, f, discrete = True):
            super(AnimDocument.FrameKeyframe, self).__init__(time, True)
            self.f = f
        def dump(self):
            dump = super(AnimDocument.FrameKeyframe, self).dump()
            dump['value'] = self.f
            dump['inSlope'] = 'Infinity'
            dump['outSlope'] = 'Infinity'
            return dump
        def set(self, keyframe):
            dump = super(AnimDocument.FrameKeyframe, self).set(keyframe)
            self.f = keyframe.f
            return self
        def __str__(self):
            return "[FrameKeyframe|{:.3f}] {}".format(self.time, self.f)
        def equals(self, other):
            return self.f == other.f
        def default(self):
            return self.f == 0

    class Timeline(object):
        def __init__(self, anim):
            self.anim = anim
            self.curves = {}
        def addKeyframe(self, object, keyframe):
            type = AnimType.Keyframe(keyframe)
            if (object,type) not in self.curves:
                self.curves[(object,type)] = AnimDocument.Curve(type, object)
            curve = self.curves[(object,type)]
            curve.addKeyframe(keyframe)
        def getKeyframes(self, f):
            return self.frames[f]
        def getStartTime(self):
                return 0
        def getStopTime(self):
                return (self.anim.frameCount-1)/self.anim.frameRate

    class GameObject(object):
        def __init__(self, id, name):
            self.id = id
            self.name = name
            self.children = []
        def addChild(self, object):
            if (isinstance(object,AnimDocument.GameObject)):
                self.children.append(object)
        def byId(self, id):
            for object in self.children:
                if object.id == id: return [object]
                else:
                    next = object.byId(id)
                    if next != None: return [object] + next
            return None

    def __init__(self, swf, svg, type = Type.MULTI_SVG):
        self.swf = swf
        self.svg = svg
        self.type = type
        self.frameRate = self.swf.frameRate
        self.frameCount = self.swf.frameCount
        self.timeline = AnimDocument.Timeline(self)
        self.parse()

    def parse(self):

        logging.info("<Anim> Parsing SVGDocument")
        logging.info("<Anim> Creating GameObjects...")

        # Index objects
        objects = AnimDocument.GameObject(0,'root')
        for depth in self.swf.depths.values():
            objects.addChild(AnimDocument.GameObject(depth.id, depth.name))

        logging.info("<Anim> Populating curves with keyframes...")

        # Populate curves with keyframes
        for f, frame in enumerate(self.swf.frames):
            for transform in frame:
                time = f/self.swf.frameRate
                object = objects.byId(transform.depth.id)[0]
                discrete = len(transform.depth.charHistory) > 1

                if isinstance(transform,SWFDocument.MatrixTransform):

                    try:
                        # Position
                        positionKeyframe = AnimDocument.PositionKeyframe(time, transform, discrete)
                        self.timeline.addKeyframe(object, positionKeyframe)
                    except AssertionError, e: pass
                    try:
                        # Position
                        scaleKeyframe = AnimDocument.ScaleKeyframe(time, transform, discrete)
                        self.timeline.addKeyframe(object, scaleKeyframe)
                    except AssertionError, e: pass
                    try:
                        # Position
                        eulerKeyframe = AnimDocument.EulerKeyframe(time, transform, discrete)
                        self.timeline.addKeyframe(object, eulerKeyframe)
                    except AssertionError, e: pass

                # Active frame
                try:
                    isActiveKeyframe = AnimDocument.IsActiveKeyframe(time, transform, discrete)
                    self.timeline.addKeyframe(object, isActiveKeyframe)
                except AssertionError, e: pass

                # FrameKeyframe
                # if layer has more than one frame, add a frameKeyframe to it
                if (discrete):
                    try:
                        frame = transform.depth.childHistory.index(transform.f)
                        frameKeyframe = AnimDocument.FrameKeyframe(time, frame, discrete)
                        self.timeline.addCurveKeyframe(object, frameKeyframe)
                    except AssertionError, e: pass

        logging.info('<Anim> Optmizing curves...')
        c_before = sum([1 for c in self.timeline.curves])
        k_before = sum([sum([1 for k in c.keyframes]) for c in self.timeline.curves.values()])

        for curve in self.timeline.curves.values():
            curve.optimize()
        self.timeline.curves = {c:self.timeline.curves[c] for c in self.timeline.curves if self.timeline.curves[c].hasKeyframes()}

        c_after = sum([1 for c in self.timeline.curves])
        k_after = sum([sum([1 for k in c.keyframes]) for c in self.timeline.curves.values()])
        logging.info('<Anim> before: {} curves / {} keyframes'.format(c_before, k_before))
        logging.info('<Anim> after: {} curves / {} keyframes'.format(c_after, k_after))

        logging.debug('<Anim> Curves:')
        for curve in self.timeline.curves.values():
            logging.debug('\t{}'.format(curve))
            for keyframe in curve.keyframes:
                logging.debug('\t\t{}'.format(keyframe))

    def export(self, rootFolder, folder):
        ## Debug Output
        logging.info("<Anim> Parsing template file {}/{}".format(rootFolder, ANIM_TEMPLATE))
        anim_template = open("{}/{}".format(rootFolder, ANIM_TEMPLATE), 'r')
        try:
            anim = yaml.load(anim_template)
        except yaml.YAMLError as exc:
            logging.error(exc)

        # Set template sample/frame rate
        anim['AnimationClip']['m_Name'] = self.swf.alias
        anim['AnimationClip']['m_SampleRate'] = self.frameRate
        anim['AnimationClip']['m_AnimationClipSettings']['m_StartTime'] = self.timeline.getStartTime()
        anim['AnimationClip']['m_AnimationClipSettings']['m_StopTime'] = self.timeline.getStopTime()

        logging.info("<Anim> Writing header\n\t\tm_Name : {}\n\t\tm_SampleRate : {}\n\t\tm_StartTime : {}\n\t\tm_StopTime : {}".format(anim['AnimationClip']['m_Name'], self.frameRate, 0, (self.frameCount-1)/self.frameRate))

        # Clear template
        anim['AnimationClip']['m_EditorCurves'] = []
        anim['AnimationClip']['m_PositionCurves'] = []
        anim['AnimationClip']['m_ScaleCurves'] = []
        anim['AnimationClip']['m_EulerCurves'] = []
        anim['AnimationClip']['m_FloatCurves'] = []

        # Merge curves into template
        for curve in self.timeline.curves.values():
            type = ''
            tag = ''
            if (curve.type == AnimType.POSITION):
                tag = 'm_PositionCurves'
            elif (curve.type == AnimType.SCALE):
                tag = 'm_ScaleCurves'
            elif (curve.type == AnimType.EULER):
                tag = 'm_EulerCurves'
            elif (curve.type == AnimType.ISACTIVE or curve.type == AnimType.FRAME):
                tag = 'm_FloatCurves'

            logging.debug('<Anim> Merging {} into template'.format(curve))
            anim['AnimationClip'][tag].append(curve.dump())

        logging.info("<Anim> Exporting animation to {}.anim".format(self.swf.alias))
        anim_file = open('{}/{}.anim'.format(folder,self.swf.alias), 'wb')
        anim_file.write("%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n--- !u!74 &0\n")
        anim_file.write(yaml.dump(anim))
