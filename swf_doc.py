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
            return '[SPRITE|{}] (shape.id: {}, frameCount: {}, depth: {}, matrix: {})'.format(self.id, self.shape.id, self.frameCount, self.depth, self.matrix)
        def nametag(self):
            return '[SPRITE|{}]'.format(self.id)

    class Frame(object):
        def __init__(self, f, char, matrix, depth):
            self.f = f
            self.char = char
            self.matrix = matrix
            self.depth = depth

    ##
    #   constructor

    def __init__(self, file, depthNames={}):
        self.depthNames = depthNames
        # load and parse the SWF
        logging.info("<SWF> Starting parse...")
        self.swf = SWF(open(file, 'rb'))
        self.alias = file.split('.')[0];
        self.frameRate = self.swf.header.frame_rate
        self.frameCount = self.swf.header.frame_count

        # Debug
        logging.debug(self.swf)

        # Document ELements
        self.shapes = list()
        self.sprites = list()
        self.frames = list()
        self.depthGroups = dict()
        for _ in range(self.frameCount):
            self.frames.append(list())

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
                lastDefinedSprite = Sprite(lastDefinedShape)
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
                lastDefinedShape = self.MorphShape(tag)
                logging.info("<SWF> {} created".format(lastDefinedShape))
                shapes.append(lastDefinedShape)

            # [PlaceObject2]
            elif (tag.type == 26):

                # Find char associated to this depth
                char = self.getCharacterByDepth(tag.depth)

                if (tag.hasCharacter):
                    # If another char is in this depth, remove it and refer to the new
                    # Also set sharedDepth so SVGDocument can group these shapes into layered files (optional)
                    if (char != None and char.id != tag.characterId):
                        logging.debug("<SWF> Removing [CHAR|{}] from depth {}".format(char.id,tag.depth))
                        char.depth = -1
                        self.frames[f].append(SWFDocument.Frame(f, char, None, -1))
                    # Find new char and set depth
                    char = self.getCharacterById(tag.characterId)
                    if (char != None):
                        logging.debug("<SWF> Moving [CHAR|{}] to depth {}".format(tag.characterId,tag.depth))
                        char.depth = tag.depth
                        if (tag.depth not in self.depthGroups):
                            self.depthGroups[tag.depth] = list()
                        if (char.id not in self.depthGroups[tag.depth]):
                            self.depthGroups[tag.depth].append(char.id)
                    else:
                        logging.error("<SWF> Couldn't find [CHAR|{}]".format(tag.characterId))
                        continue

                matrix = None
                if tag.hasMatrix:
                    matrix = TMatrix(tag.matrix.to_array())
                elif tag.hasCharacter:
                    matrix = TMatrix()

                if matrix != None:
                    if (isinstance(char,SWFDocument.Sprite)): matrix = matrix * char.matrix
                    elif (isinstance(char,SWFDocument.Shape)): matrix = matrix * char.getCenterMatrix()

                logging.debug("<SWF> f{} [CHAR|{}] matrix: {}, depth: {}".format(f, tag.characterId, matrix, tag.depth))
                self.frames[f].append(SWFDocument.Frame(f, char, matrix, tag.depth))

            # [ShowFrame]
            elif (tag.type == 1 and f < self.frameCount):
                logging.debug("<SWF> Show frame: {}".format(f))
                f += 1;

        ## Debug Output
        logging.debug("<SWF> Shapes:")
        for shape in self.shapes:
            logging.debug('\t{}'.format(shape))
        logging.debug("<SWF> Depth Groups:")
        for depth, tags in self.depthGroups.iteritems():
            logging.debug('\tdepth: {}'.format(depth))
            for tag in tags:
                logging.debug('\t\t{}'.format(tag))
        logging.debug("<SWF> Sprites:")
        for sprite in self.sprites:
            logging.debug('\t{}'.format(sprite))
        logging.debug("<SWF> Frames:")
        for f, frame in enumerate(self.frames):
            logging.debug("\t[frame{}]".format(f))
            for k, keyframe in enumerate(frame):
                logging.debug("\t\t[key{}] : char {} : matrix {} : depth {}".format(k, keyframe.char.nametag(), keyframe.matrix, keyframe.depth))

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
