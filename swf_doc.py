import logging
from swf.movie import SWF
from model import TMatrix

class SWFDocument(object):

    ##
    #   MODEL

    class Character(object):
        def __init__(self, tag):
            self.tag = tag
            self.id = tag.characterId
            self.depth = -1
        def nametag(self):
            return '[CHAR|{}]'.format(self.id)

    class Shape(Character):
        def __init__(self, tag):
            self.bounds = tag.shape_bounds
            super(SWFDocument.Shape, self).__init__(tag)
        def __str__(self):
            return '[SHAPE|{}] centerMatrix: {}'.format(self.id, self.getCenterMatrix())
        def nametag(self):
            return '[SHAPE|{}]'.format(self.id)
        def getCenterMatrix(self):
            return [1,0,0,1,self.bounds.xmin+(self.bounds.xmax-self.bounds.xmin)/2,self.bounds.ymin+(self.bounds.ymax-self.bounds.ymin)/2]

    class MorphShape(Shape):
        def __init__(self, tag):
            self.ratio = 0
            tag.shape_bounds = tag.startBounds
            super(SWFDocument.MorphShape, self).__init__(tag)
        def __str__(self):
            return '[MORPH|{}] centerMatrix: {}'.format(self.id, self.getCenterMatrix())
        def nametag(self):
            return '[MORPH|{}]'.format(self.id)

    class Sprite(Character):
        def __init__(self, tag, shape):
            super(SWFDocument.Sprite, self).__init__(tag)
            self.frameCount = tag.frameCount
            self.shape = shape
            self.matrix = None
        def __str__(self):
            return '[SPRITE|{}] (shape.id: {}, frameCount: {}, matrix: {})'.format(self.id, self.shape.id, self.frameCount, self.matrix)
        def nametag(self):
            return '[SPRITE|{}]'.format(self.id)

    class Transform(object):
        def __init__(self, f, char, depth):
            self.f = f
            self.char = char
            self.depth = depth
        def __str__(self):
            return "[Transform] char:{} depth:{}".format(self.char, self.depth)

    class MatrixTransform(Transform):
        def __init__(self, f, char, depth, matrix):
            self.matrix = matrix
            super(SWFDocument.MatrixTransform, self).__init__(f, char, depth)
        def __str__(self):
            return "[MatrixTransform] char:{} depth:{} matrix:{}".format(self.char, self.depth, self.matrix)

    class Frame(object):
        @staticmethod
        def addFrame(swf):
            swf.frames.append([])
        @staticmethod
        def getFrame(swf, f):
            return swf.frames[f]

    class Depth(object):
        @staticmethod
        def get(swf, depth):
            if depth not in swf.depths:
                swf.depths[depth] = SWFDocument.Depth(depth,str(depth),None)
            return swf.depths[depth]
        def __init__(self, id, name, char):
            self.id = id
            self.name = name
            self.charHistory = []
            self.char = None
            self.setChar(char)
        def setChar(self, char):
            if not char: return
            if char not in self.charHistory: self.charHistory.append(char)
            self.char = char
        def removeChar(self):
            self.char = None
        def __str__(self):
            return "[Depth|{}]".format(self.id)

    ##
    #   constructor

    def __init__(self, file, depthNames={}):
        self.depthNames = depthNames
        # load and parse the SWF
        logging.info("<SWF> Starting parse...")
        self.swf = SWF(open(file, 'rb'))
        self.alias = file.split('.')[0].split('/')[-1];
        self.frameRate = self.swf.header.frame_rate
        self.frameCount = self.swf.header.frame_count

        # Debug
        logging.debug(self.swf)

        # Document ELements
        self.shapes = []
        self.sprites = []
        self.frames = []
        self.depths = {}

        for _ in range(self.frameCount):
            SWFDocument.Frame.addFrame(self)

        # Parse
        self.parse()

    ##
    #   PARSING

    def parse(self):
        logging.info("<SWF> Starting parsing...")

        f = 0
        lastDefinedShape = None
        lastDefinedSprite = None
        for tag in self.swf.tags:

            # [DefineShape], [DefineShape2], [DefineShape3], [DefineShape4]
            if (tag.type == 2 or tag.type == 22 or tag.type == 32 or tag.type == 83):
                # Create shape model
                lastDefinedShape = SWFDocument.Shape(tag)
                logging.info("<SWF> {} created".format(lastDefinedShape))
                self.shapes.append(lastDefinedShape)

            # [DefineSprite]
            elif (tag.type == 39):
                lastDefinedSprite = SWFDocument.Sprite(tag, lastDefinedShape)
                for tagtag in tag.tags:
                    # [PlaceObejct2]
                    if (tagtag.type == 26):
                        lastDefinedSprite.matrix = tagtag.matrix.to_array()
                        break
                    print(tagtag)
                logging.info("<SWF> {} created".format(lastDefinedSprite))
                self.sprites.append(lastDefinedSprite)

            # [DefineMorphShape]
            elif tag.type == 46:
                lastDefinedShape = self.MorphShape(tag)
                logging.info("<SWF> {} created".format(lastDefinedShape))
                self.shapes.append(lastDefinedShape)

            # [PlaceObject2]
            elif (tag.type == 26):
                depth = SWFDocument.Depth.get(self, tag.depth)
                if (tag.instanceName):
                    depth.name = tag.instanceName

                if (tag.hasCharacter):
                    # Place/replace character in the current depth
                    if not tag.hasMove:
                        char = depth.char
                        # If another char is in this depth, remove it (also add frame to update depth)
                        if (char != None and char.id != tag.characterId):
                            logging.debug("<SWF> Removing >{}< from {}".format(char,depth))
                            char.depth = None
                            depth.removeChar()
                            self.frames[f].append(SWFDocument.Transform(f, None, depth))
                        # Find new char and set depth
                        char = self.getCharacterById(tag.characterId)
                        if (char != None):
                            logging.debug("<SWF> Moving >{}< to {}".format(char,depth))
                            char.depth = depth
                            depth.setChar(char)
                            self.frames[f].append(SWFDocument.MatrixTransform(f, char, depth, TMatrix(tag.matrix.to_array())))
                        else:
                            logging.error("<SWF> Couldn't find [Char|{}]".format(tag.characterId))
                    # Remove character in the current depth
                    else:
                        char = depth.char
                        logging.debug("<SWF> Removing >{}< from {}".format(char,depth))
                        char.depth = None
                        depth.removeChar()
                        self.frames[f].append(SWFDocument.Transform(f, None, depth))
                else:
                    if not tag.hasMove:
                        logging.error("<SWF> I don't really know what was supposed to happen here; docs says it should crash. Savage.")
                    # Alter the character at the specified depth
                    else:
                        matrix = None
                        if tag.hasMatrix:
                            matrix = TMatrix(tag.matrix.to_array())

                        if matrix != None:
                            if (isinstance(char,SWFDocument.Sprite)): matrix = matrix * char.matrix
                            elif (isinstance(char,SWFDocument.Shape)): matrix = matrix * char.getCenterMatrix()

                        logging.debug("<SWF> f{} >{}< matrix: {}, {}".format(f, char, matrix, depth))
                        self.frames[f].append(SWFDocument.MatrixTransform(f, char, depth, matrix))

            # [ShowFrame]
            elif (tag.type == 1 and f < self.frameCount):
                logging.debug("<SWF> Show frame: {}".format(f))
                f += 1;

        ## Debug Output
        logging.debug("<SWF> Shapes:")
        for shape in self.shapes:
            logging.debug('\t{}'.format(shape))
        logging.debug("<SWF> Sprites:")
        for sprite in self.sprites:
            logging.debug('\t{}'.format(sprite))
        logging.debug("<SWF> Frames:")
        for f, frame in enumerate(self.frames):
            logging.debug("\t[frame{}]".format(f))
            for t, transform in enumerate(frame):
                logging.debug("\t\t{}".format(transform))
        logging.debug("<SWF> Depths:")
        for d, depth in self.depths.iteritems():
            logging.debug("\t{}".format(depth))
            logging.debug("\tname: {}".format(depth.name))
            logging.debug("\thistory:")
            for c, char in enumerate(depth.charHistory):
                logging.debug("\t\t{}".format(char))

    def getCharacterById(self, id):
        shape = [s for s in self.shapes if s.id == id]
        sprite = [s for s in self.sprites if s.id == id]
        if (len(shape)): return shape[0]
        elif (len(sprite)): return sprite[0]
        else: return None

    def getCharacterByDepth(self, depth):
        shape = [s for s in self.shapes if s.depth == depth]
        sprite = [s for s in self.sprites if s.depth == depth]
        if (len(shape)): return shape[0]
        elif (len(sprite)): return sprite[0]
        else: return None

    def getDepthName(self, depth):
        if depth in self.depthNames:
            return self.depthNames[depth]
        else:
            return depth
