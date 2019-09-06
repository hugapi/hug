import io

import hug
from matplotlib import pyplot


@hug.get(output=hug.output_format.png_image)
def plot():
    pyplot.plot([1, 2, 3, 4])
    pyplot.ylabel('some numbers')

    image_output = io.BytesIO()
    pyplot.savefig(image_output, format='png')
    image_output.seek(0)
    return image_output
