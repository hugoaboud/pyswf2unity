import logging
from swf.export import SVGExporter
from swf.tag import TagShowFrame, TagPlaceObject, TagRemoveObject, TagDefineShape, TagDefineMorphShape, TagDefineSprite
from swf.export import XLINK_HREF
from lxml import etree

from model import TMatrix
from config import unit_divisor
from swf_doc import SWFDocument

class ComposedSVGExporter(SVGExporter):
    """
    An SVG exporter which knows how to export a single shape.
    """
    def __init__(self, document, margin=0):
        self.document = document
        self.frame = None
        self.shape_tags = []
        self.display_tags = []
        super(ComposedSVGExporter, self).__init__(margin = margin)

    def export_all(self, swf):
        self.shape_tags = [tag for tag in swf.tags if isinstance(tag,TagDefineShape) or isinstance(tag,TagDefineMorphShape)]
        return super(ComposedSVGExporter, self).export(swf)

    def getDisplayTagById(self, tags, id):
        for tag in tags:
            if (isinstance(tag,TagPlaceObject)):
                if tag.characterId == id:
                    return tag
        return None

    def export_layer(self, layer, swf):
        self.shape_tags = []
        self.display_tags = []
        for f, frame in enumerate(layer.frames):
            char = swf.getCharacterById(frame.id)
            display_tag = self.getDisplayTagById(swf.swf.tags, char.id)
            if (isinstance(char, SWFDocument.Sprite)):
                char = char.shape
                display_tag.shape_id = char.id
            shape_tag = char.tag
            if len(layer.frames) > 1:
                shape_tag.f = f
                display_tag.f = f
            if frame.f == 0:
                bounds = shape_tag.shape_bounds
                layer.center = [bounds.xmin + (bounds.xmax-bounds.xmin)/2, bounds.ymin + (bounds.ymax - bounds.ymin)/2]
                display_tag.matrix = TMatrix().getSWFMatrix()
            else:
                bounds = shape_tag.shape_bounds
                fpos = [bounds.xmin + (bounds.xmax-bounds.xmin)/2, bounds.ymin + (bounds.ymax - bounds.ymin)/2]
                display_tag.matrix = TMatrix().setPosition([
                                layer.center[0] - fpos[0],
                                layer.center[1] - fpos[1]]
                             ).getSWFMatrix()
            self.shape_tags.append(shape_tag)
            self.display_tags.append(display_tag)
        return super(ComposedSVGExporter, self).export(swf.swf)

    def export_frame(self, frame, swf):
        self.shape_tags = [swf.getCharacterById(frame.id).tag]
        self.display_tags = [self.getDisplayTagById(swf.swf.tags, frame.id)]
        return super(ComposedSVGExporter, self).export(swf.swf)

    def export_shape(self, shape, swf):
        self.shape_tags = [swf.getCharacterById(shape.id).tag]
        self.display_tags = [self.getDisplayTagById(swf.swf.tags, shape.id)]
        return super(ComposedSVGExporter, self).export(swf.swf)

    def get_shape_tags(self, tags):
        return super(ComposedSVGExporter, self).get_shape_tags(self.shape_tags)

    def get_display_tags(self, tags, z_sorted=True):
        return super(ComposedSVGExporter, self).get_display_tags(self.display_tags, z_sorted)

    def export_define_shape(self, tag):
        self.shape_exporter.force_stroke = self.force_stroke
        super(ComposedSVGExporter, self).export_define_shape(tag)
        shape = self.shape_exporter.g
        if (hasattr(tag,'f')):
            shape.set("id", "f:%d" % tag.f)
        else:
            shape.set("id", "%d" % tag.characterId)

    def export_display_list_item(self, tag, parent=None):
        use = super(ComposedSVGExporter, self).export_display_list_item(tag, parent)
        if (hasattr(tag,'f')):
            use.set(XLINK_HREF, "#f:%s" % tag.f)
        elif (hasattr(tag,'shape_id')):
            use.set(XLINK_HREF, "%s" % tag.shape_id)
        else:
            use.set(XLINK_HREF, "#%s" % tag.characterId)
        return use


class SVGDocument(object):

    class Type:
        SHAPE = 0
        DEPTH = 1
        DEPTH_MULTI = 2
        ALL = 99

    class Frame(object):
        def __init__(self, f, id):
            self.f = f
            self.id = id

    class Layer(object):
        def __init__(self, name):
            self.name = name
            self.frames = list()
            self.center = [0,0]
        def addFrame(self, id):
            frame = SVGDocument.Frame(len(self.frames),id)
            self.frames.append(frame)
        def __str__(self):
            return str(self.name)
        @staticmethod
        def getFrameById(layers, id):
            for layer in layers:
                for frame in layer.frames:
                    if frame.id == id:
                        return [layer, frame]

    def __init__(self, swfDocument, type = Type.DEPTH_MULTI):
        self.exporter = ComposedSVGExporter(self)
        self.swf = swfDocument
        self.type = type
        self.parse()

    def parse(self):
        self.layers = []
        logging.info("<SVG> Parsing SWFDocument")

        if type == SVGDocument.Type.DEPTH or SVGDocument.Type.DEPTH_MULTI:
            for d, depth in self.swf.depths.iteritems():
                layer = SVGDocument.Layer(depth.name)
                for char in depth.charHistory:
                    layer.addFrame(char.id)
                self.layers.append(layer)

            logging.debug("<SVG> Layers:")
            for l, layer in enumerate(self.layers):
                logging.debug("\t[layer{}] name: {}".format(l, layer))
                for f, frame in enumerate(layer.frames):
                    logging.debug("\t\t[frame{}] : id {}".format(f, frame.id))

    def export(self, folder, all = False):
        # Parse
        logging.info("<SVG> Exporting SVGDocument")

        if self.type == SVGDocument.Type.DEPTH:
            for layer in self.layers:
                if (len(layer.frames) > 1):
                    logging.info("<SVG> Exporting animated layer {} to {}_f.svg".format(layer,layer))
                    open('{}/{}_f.svg'.format(folder,layer), 'wb').write(self.exporter.export_layer(layer, self.swf).read())
                else:
                    logging.info("<SVG> Exporting layer {} to {}.svg".format(layer,layer))
                    open('{}/{}.svg'.format(folder,layer), 'wb').write(self.exporter.export_layer(layer, self.swf).read())

        elif self.type == SVGDocument.Type.DEPTH_MULTI:
            for layer in self.layers:
                if (len(layer.frames) > 1):
                    for f, frame in enumerate(layer.frames):
                        logging.info("<SVG> Exporting layer {} frame {} to {}_{}.svg".format(layer,f,layer,f))
                        open('{}/{}_{}.svg'.format(folder,layer,f), 'wb').write(self.exporter.export_frame(frame, self.swf).read())
                else:
                    logging.info("<SVG> Exporting layer {} to {}.svg".format(layer,layer))
                    open('{}/{}.svg'.format(folder,layer), 'wb').write(self.exporter.export_layer(layer, self.swf).read())

        elif self.type == SVGDocument.Type.SHAPE:
            for shape in self.swf.shapes:
                logging.info("<SVG> Exporting shape {} to {}.svg".format(shape,shape.id))
                open('{}/{}.svg'.format(folder,shape.id), 'wb').write(self.exporter.export_shape(shape, self.swf).read())

        elif self.type == SVGDocument.Type.ALL:
            logging.info("<SVG> Exporting all frames to {}/{}.svg".format(folder,self.swf.alias))
            open('{}/{}.svg'.format(folder,self.swf.alias), 'wb').write(self.exporter.export_all(self.swf).read())
