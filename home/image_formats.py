from wagtail.images.formats import Format, register_image_format

register_image_format(Format('right-200', 'right-200', 'richtext-image right', 'width-200'))
register_image_format(Format('left-200', 'left-200', 'richtext-image left', 'width-200'))
