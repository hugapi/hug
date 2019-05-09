import hug
from PIL import Image, ImageDraw


@hug.get("/image.png", output=hug.output_format.png_image)
def create_image():
    image = Image.new("RGB", (100, 50))  # create the image
    ImageDraw.Draw(image).text((10, 10), "Hello World!", fill=(255, 0, 0))
    return image
