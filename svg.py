import logging
from swf.export import SVGExporter
from swf.tag import TagShowFrame, TagPlaceObject, TagRemoveObject, TagDefineShape, TagDefineMorphShape
from swf.export import XLINK_HREF

class ComposedSVGExporter(SVGExporter):
    """
    An SVG exporter which knows how to export a single shape.
    """
    def __init__(self, margin=0):
        self.frame = None
        self.shape_tags = []
        super(ComposedSVGExporter, self).__init__(margin = margin)

    def export_all(self, swf):
        self.shape_tags = [tag for tag in swf.tags if isinstance(tag,TagDefineShape) or isinstance(tag,TagDefineMorphShape)]
        return super(ComposedSVGExporter, self).export(swf)

    def export_layer(self, layer, swf):
        self.shape_tags = []
        if (len(layer.frames) == 1):
            for tag in swf.tags:
                if (isinstance(tag,TagDefineShape) or isinstance(tag,TagDefineMorphShape)):
                    if tag.characterId == layer.frames[0].id:
                        self.shape_tags.append(tag)
        else:
            for tag in swf.tags:
                if (isinstance(tag,TagDefineShape) or isinstance(tag,TagDefineMorphShape)):
                    for f, frame in enumerate(layer.frames):
                        if tag.characterId == frame.id:
                            tag.f = f
                            self.shape_tags.append(tag)
        return super(ComposedSVGExporter, self).export(swf)

    def export_frame(self, frame, swf):
        for tag in swf.tags:
            if (isinstance(tag,TagDefineShape) or isinstance(tag,TagDefineMorphShape)):
                if tag.characterId == frame.id:
                    self.shape_tags = [tag]
                    return super(ComposedSVGExporter, self).export(swf)
        return None

    def export_shape(self, shape, swf):
        for tag in swf.tags:
            if (isinstance(tag,TagDefineShape) or isinstance(tag,TagDefineMorphShape)):
                if tag.characterId == shape.id:
                    self.shape_tags = [tag]
                    return super(ComposedSVGExporter, self).export(swf)
        return None

    def get_shape_tags(self, tags):
        return super(ComposedSVGExporter, self).get_shape_tags(self.shape_tags)

    def get_display_tags(self, tags, z_sorted=True):
        display_tags = []
        for tag in tags:
            if isinstance(tag, TagPlaceObject):
                for shape_tag in self.shape_tags:
                    if tag.characterId == shape_tag.characterId:
                        if tag.characterId not in [t.characterId for t in display_tags]:
                            if (hasattr(shape_tag,'f')):
                                tag.f = shape_tag.f
                            display_tags.append(tag)
        return super(ComposedSVGExporter, self).get_display_tags(display_tags, z_sorted)

    def export_define_shape(self, tag):
        self.shape_exporter.force_stroke = self.force_stroke
        super(ComposedSVGExporter, self).export_define_shape(tag)
        shape = self.shape_exporter.g
        if (hasattr(tag,'f')):
            shape.set("id", "%d" % tag.f)
        else:
            shape.set("id", "%d" % tag.characterId)

    def export_display_list_item(self, tag, parent=None):
        use = super(ComposedSVGExporter, self).export_display_list_item(tag, parent)
        if (hasattr(tag,'f')):
            use.set(XLINK_HREF, "#%s" % tag.f)
        else:
            use.set(XLINK_HREF, "#%s" % tag.characterId)
        return use


class SVGDocument(object):

    class Frame(object):
        def __init__(self, f, id):
            self.f = f
            self.id = id

    class Layer(object):
        def __init__(self, name):
            self.name = name
            self.frames = list()
        def addFrame(self, tag):
            self.frames.append(SVGDocument.Frame(len(self.frames),tag))
        def __str__(self):
            return self.name

    def __init__(self, swfDocument, groupByDepth = True):
        self.exporter = ComposedSVGExporter()
        self.swf = swfDocument
        self.groupByDepth = groupByDepth
        self.parse()

    def parse(self):
        logging.info("<SVG> Parsing SWFDocument")

        if self.groupByDepth:
            self.layers = []
            for depth, ids in self.swf.depthGroups.iteritems():
                layer = SVGDocument.Layer(self.swf.getDepthName(depth))
                for id in ids:
                    layer.addFrame(id)
                self.layers.append(layer)

            logging.debug("<SVG> Layers:")
            for l, layer in enumerate(self.layers):
                logging.debug("\t[layer{}] name: {}".format(l, layer))
                for f, frame in enumerate(layer.frames):
                    logging.debug("\t\t[frame{}] : id {}".format(f, frame.id))

    def export(self, folder, separateLayers = False, all = False):
        # Parse
        logging.info("<SVG> Exporting SVGDocument")

        if self.groupByDepth:
            for layer in self.layers:
                if (separateLayers and len(layer.frames) > 1):
                    for f, frame in enumerate(layer.frames):
                        logging.info("<SVG> Exporting layer {} frame {} to {}_{}.svg".format(layer,f,layer,f))
                        open('{}/{}_{}.svg'.format(folder,layer,f), 'wb').write(self.exporter.export_frame(frame, self.swf.swf).read())
                else:
                    logging.info("<SVG> Exporting layer {} to {}.svg".format(layer,layer))
                    open('{}/{}.svg'.format(folder,layer), 'wb').write(self.exporter.export_layer(layer, self.swf.swf).read())
        else:
            for shape in self.swf.shapes:
                logging.info("<SVG> Exporting shape {} to {}.svg".format(shape,shape.id))
                open('{}/{}.svg'.format(folder,shape.id), 'wb').write(self.exporter.export_shape(shape, self.swf.swf).read())

        if all:
            logging.info("<SVG> Exporting all frames to {}/{}.svg".format(folder,self.swf.alias.split('/')[-1]))
            open('{}/{}.svg'.format(folder,self.swf.alias.split('/')[-1]), 'wb').write(self.exporter.export_all(self.swf.swf).read())