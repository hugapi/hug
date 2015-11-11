'''A simple streaming movie server example'''
import hug


@hug.get(output=hug.output_format.mp4_video)
def watch():
    '''Watch an example movie, streamed directly to you from hug'''
    return 'movie.mp4'
