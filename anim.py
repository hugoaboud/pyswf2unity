import logging
import yaml

from config import ANIM_TEMPLATE
from model import AnimType

class AnimDocument(object):

    class Curve(object):
        def __init__(self, type, object):
            self.object = object
            self.type = type
            self.keyframes = list()
        def dump(self):
            dump = dict({'curve':dict()})
            dump['curve']['serializedVersion'] = 2
            dump['path'] = str(self.object)
            dump['curve']['m_PreInfinity'] = 2
            dump['curve']['m_PostInfinity'] = 2
            dump['curve']['m_RotationOrder'] = 4
            dump['curve']['m_Curve'] = self.keyframes
            if (self.type == AnimType.ISACTIVE):
                dump['attribute'] = 'm_IsActive'
                dump['classID'] = 1
                dump['script'] = dict({'fileID':0})
            return dump
        def addKeyframe(self, keyframe):
            #replace keyframes of the same type on the same time
            for k, key in enumerate(self.keyframes):
                if (type(key) == type(keyframe) and key.time == keyframe.time):
                    self.keyframes[k].set(keyframe)
                    return
            self.keyframes.append(keyframe)
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

        def __str__(self):
            return "[{}|{}]".format(self.object.name, AnimType.Name(self.type))

    class Keyframe (object):
        def __init__(self, frame, frameRate):
            self.time = frame.f / frameRate
        def dump(self):
            dump = dict()
            dump['serializedVersion'] = 2
            dump['time'] = self.time
            dump['value'] = dict({'x': 0, 'y': 0, 'z': 0})
            dump['inSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
            dump['outSlope'] = dict({'x': 0, 'y': 0, 'z': 0})
            dump['tangentMode'] = 0
            return dump
        def set(self, keyframe):
            keyframe.time = self.time
            return
        def __str__(self):
            return "[Keyframe|{}]".format(self.time)
        def equals(self, other):
            return False

    class PositionKeyframe(Keyframe):
        def __init__(self, frame, frameRate):
            assert frame.matrix != None
            self.position = frame.matrix.getPosition()
            super(AnimDocument.PositionKeyframe, self).__init__(frame, frameRate)
        def dump(self, frameRate):
            dump = super(AnimDocument.PositionKeyframe, self).dump(frameRate)
            dump['value']['x'] = self.position[0]
            dump['value']['y'] = -self.position[1]
            return dump
        def set(self, keyframe):
            self.position = keyframe.position
            return
        def __str__(self):
            return "[PositionKeyframe|{:.3f}] {}".format(self.time, self.position)
        def equals(self, other):
            return self.position == other.position

    class ScaleKeyframe(Keyframe):
        def __init__(self, frame, frameRate):
            assert frame.matrix != None
            self.scale = frame.matrix.getScale()
            super(AnimDocument.ScaleKeyframe, self).__init__(frame, frameRate)
        def dump(self, frameRate):
            dump = super(AnimDocument.ScaleKeyframe, self).dump(frameRate)
            dump['value']['x'] = self.scale[0]
            dump['value']['y'] = self.scale[1]
            return dump
        def set(self, keyframe):
            self.scale = keyframe.scale
            return
        def __str__(self):
            return "[ScaleKeyframe|{:.3f}] {}".format(self.time, self.scale)
        def equals(self, other):
            return self.scale == other.scale

    class EulerKeyframe(Keyframe):
        def __init__(self, frame, frameRate):
            assert frame.matrix != None
            self.euler = frame.matrix.getEuler()
            super(AnimDocument.EulerKeyframe, self).__init__(frame, frameRate)
        def dump(self, frameRate):
            dump = super(AnimDocument.EulerKeyframe, self).dump(frameRate)
            dump['value']['z'] = self.euler
            return dump
        def set(self, keyframe):
            self.euler = keyframe.euler
            return
        def __str__(self):
            return "[EulerKeyframe|{:.3f}] {}".format(self.time, self.euler)
        def equals(self, other):
            return self.euler == other.euler

    class IsActiveKeyframe(Keyframe):
        def __init__(self, frame, frameRate):
            super(AnimDocument.IsActiveKeyframe, self).__init__(frame, frameRate)
            self.active = 1.0 if frame.depth >= 0 else 0.0
        def dump(self, frameRate):
            dump = super(AnimDocument.IsActiveKeyframe, self).dump(frameRate)
            dump['value'] = self.active
            dump['tangentMode'] = 103
            dump['inSlope'] = 'Infinity'
            dump['outSlope'] = 'Infinity'
            return dump
        def set(self, keyframe):
            self.active = keyframe.active
            return
        def __str__(self):
            return "[IsActiveKeyframe|{:.3f}] {}".format(self.time, self.active)
        def equals(self, other):
            return self.active == other.active

    class Timeline(object):
        def __init__(self, anim):
            self.anim = anim
            self.curves = list()
        def addKeyframe(self, keyframe):
            self.frames[keyframe.f].append(keyframe)
        def addCurveKeyframe(self, f, object, type, keyframe):
            curve = [c for c in self.curves if (c.object == object and c.type == type)]
            if not len(curve):
                logging.error("<ANIM> No curve found for object '{}' with type {}".format(object.name, AnimType.Name(type)))
                return
            curve = curve[0]
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

    def __init__(self, rootFolder, swf, svg):
        self.swf = swf
        self.svg = svg
        self.frameRate = self.swf.frameRate
        self.frameCount = self.swf.frameCount
        self.timeline = AnimDocument.Timeline(self)
        logging.info("<ANIM> Parsing template file {}/{}".format(rootFolder, ANIM_TEMPLATE))
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

        logging.info("<ANIM> Writing header\n\t\tm_Name : {}\n\t\tm_SampleRate : {}\n\t\tm_StartTime : {}\n\t\tm_StopTime : {}".format(anim['AnimationClip']['m_Name'], self.frameRate, 0, (self.frameCount-1)/self.frameRate))

        # Clear template
        anim['AnimationClip']['m_EditorCurves'] = []
        anim['AnimationClip']['m_PositionCurves'] = []
        anim['AnimationClip']['m_ScaleCurves'] = []
        anim['AnimationClip']['m_EulerCurves'] = []

        self.parse()

    def parse(self):

        logging.info("<Anim> Parsing SVGDocument")
        logging.info("<Anim> Creating curves...")

        # Index objects
        objects = AnimDocument.GameObject(0,'root')
        if self.svg.groupByDepth:
            for layer in self.svg.layers:
                layerObject = AnimDocument.GameObject(layer.frames[0].id,layer.name)
                for f, frame in enumerate(layer.frames):
                    layerObject.addChild(AnimDocument.GameObject(frame.id,"frame:{}".format(f)))
                objects.addChild(layerObject)
        else:
            for char in (self.swf.sprites + self.swf.shapes):
                objects.addChild(AnimDocument.Object(char.id, char.id))

        for object in objects.children:
            self.timeline.curves.append(AnimDocument.Curve(AnimType.POSITION, object))
            self.timeline.curves.append(AnimDocument.Curve(AnimType.SCALE, object))
            self.timeline.curves.append(AnimDocument.Curve(AnimType.EULER, object))
            self.timeline.curves.append(AnimDocument.Curve(AnimType.ISACTIVE, object))

        logging.info("<Convert> (anim) Populating curves...")

        # Populate curves with keyframes
        for f, time in enumerate(self.swf.frames):
            for k, frame in enumerate(time):
                try:
                    # Position
                    positionKeyframe = AnimDocument.PositionKeyframe(frame, self.swf.frameRate)
                    self.timeline.addCurveKeyframe(f/self.swf.frameRate, objects.byId(frame.char.id)[0], AnimType.POSITION, positionKeyframe)
                except AssertionError, e: pass
                try:
                    # Scale
                    scaleKeyframe = AnimDocument.ScaleKeyframe(frame, self.swf.frameRate)
                    self.timeline.addCurveKeyframe(f/self.swf.frameRate, objects.byId(frame.char.id)[0], AnimType.SCALE, scaleKeyframe)
                except AssertionError, e: pass
                try:
                    # Euler (rotation)
                    eulerKeyframe = AnimDocument.EulerKeyframe(frame, self.swf.frameRate)
                    self.timeline.addCurveKeyframe(f/self.swf.frameRate, objects.byId(frame.char.id)[0], AnimType.EULER, eulerKeyframe)
                except AssertionError, e: pass
                try:
                    # Active frame
                    isActiveKeyframe = AnimDocument.IsActiveKeyframe(frame, self.swf.frameRate)
                    self.timeline.addCurveKeyframe(f/self.swf.frameRate, objects.byId(frame.char.id)[0], AnimType.ISACTIVE, isActiveKeyframe)
                except AssertionError, e: pass

        for curve in self.timeline.curves:
            curve.optimize()

        logging.info('<ANIM> Curves:')
        for curve in self.timeline.curves:
            logging.debug('\t{}'.format(curve))
            for keyframe in curve.keyframes:
                logging.debug('\t\t{}'.format(keyframe))

    def export(self, folder):
        # Merge curves into template
        for curve in self.timeline.curves:
            type = ''
            tag = ''
            if (curve.type == AnimType.POSITION):
                type = 'PositionCurve'
                tag = 'm_PositionCurves'
            elif (curve.type == AnimType.SCALE):
                type = 'ScaleCurve'
                tag = 'm_ScaleCurves'
            elif (curve.type == AnimType.EULER):
                type = 'EulerCurve'
                tag = 'm_EulerCurves'
            elif (curve.type == AnimType.ISACTIVE):
                type = 'ActiveCurve'
                tag = 'm_FloatCurves'

            logging.info('<ANIM> Merging {}|{} into template'.format(type, curve.char.id))
            anim['AnimationClip'][tag].append(curve.dumpAnim())

        ## Debug Output
        logging.info("<ANIM> Exporting animation to {}/{}.anim".format(out_folder,alias.split('/')[-1]))

        anim_file = open('{}/{}.anim'.format(folder,self.swf.alias.split('/')[-1]), 'wb')
        anim_file.write("""%YAML 1.1
        %TAG !u! tag:unity3d.com,2011:
        --- !u!74 &7400000\n""")
        anim_file.write(yaml.dump(anim))

    def export(self, outFolder, layerNames = {}):
        pass
