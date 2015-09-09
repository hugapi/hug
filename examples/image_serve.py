import hug


@hug.get('/image.png', output=hug.output_format.png_image)
def image():
    return '../logo.png'
