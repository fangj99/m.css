import os
from docutils.parsers import rst
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives
from docutils.nodes import fully_normalize_name, whitespace_normalize_name
from docutils.parsers.rst.roles import set_classes
from docutils import nodes
from pelican import signals
from pelican import StaticGenerator

# If Pillow is not available, it's not an error unless one uses the image grid
# functionality
try:
    import PIL.Image
    import PIL.ExifTags
except ImportError:
    PIL = None

settings = {}

def configure(pelicanobj):
    settings['path'] = pelicanobj.settings.get('PATH', 'content')
    pass

class Image(Directive):
    """Image directive

    Copy of docutils.parsers.rst.directives.Image with some default classes
    added on top.
    """

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'alt': directives.unchanged,
                   'name': directives.unchanged,
                   'class': directives.class_option}

    def run(self):
        messages = []
        reference = directives.uri(self.arguments[0])
        self.options['uri'] = reference
        reference_node = None
        if 'target' in self.options:
            block = states.escape2null(
                self.options['target']).splitlines()
            block = [line for line in block]
            target_type, data = self.state.parse_target(
                block, self.block_text, self.lineno)
            if target_type == 'refuri':
                reference_node = nodes.reference(refuri=data)
            elif target_type == 'refname':
                reference_node = nodes.reference(
                    refname=fully_normalize_name(data),
                    name=whitespace_normalize_name(data))
                reference_node.indirect_reference_name = data
                self.state.document.note_refname(reference_node)
            else:                           # malformed target
                messages.append(data)       # data is a system message
            del self.options['target']

        # Add some sane default class to the image
        set_classes(self.options)
        self.options.setdefault('classes', []).append('m-image')

        image_node = nodes.image(self.block_text, **self.options)
        self.add_name(image_node)
        if reference_node:
            reference_node += image_node
            return messages + [reference_node]
        else:
            return messages + [image_node]

class ImageGrid(rst.Directive):
    has_content = True

    def run(self):
        grid_node = nodes.container()
        grid_node['classes'] += ['m-imagegrid', 'm-container-inflate']

        images = []
        total_widths = [0]
        for uri in self.content:
            # New line, calculating width from 0 again
            if not uri:
                total_widths.append(0)
                continue

            # Open the files and calculate the overall width
            absuri = uri.format(filename=os.path.join(os.getcwd(), settings['path']))
            im = PIL.Image.open(absuri)
            exif = {
                PIL.ExifTags.TAGS[k]: v
                for k, v in im._getexif().items()
                if k in PIL.ExifTags.TAGS and len(str(v)) < 256
            }
            caption = "F{}, {}/{} s, ISO {}".format(float(exif['FNumber'][0])/float(exif['FNumber'][1]), *exif['ExposureTime'], exif['ISOSpeedRatings'])
            rel_width = float(im.width)/im.height
            total_widths[-1] += rel_width
            images.append((uri, rel_width, len(total_widths) - 1, caption))

        for image in images:
            image_reference = rst.directives.uri(image[0])
            image_node = nodes.image('', uri=image_reference)
            text_nodes, _ = self.state.inline_text(image[3], self.lineno)
            text_node = nodes.paragraph('', '', *text_nodes)
            overlay_node = nodes.caption()
            overlay_node.append(text_node)
            link_node = nodes.reference('', refuri=image_reference)
            link_node.append(image_node)
            link_node.append(overlay_node)
            wrapper_node = nodes.figure(width="{}%".format(image[1]*100.0/total_widths[image[2]]))
            wrapper_node.append(link_node)
            grid_node.append(wrapper_node)

        return [grid_node]

def register():
    signals.initialized.connect(configure)

    rst.directives.register_directive('image', Image)
    rst.directives.register_directive('image-grid', ImageGrid)
