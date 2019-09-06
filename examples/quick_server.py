import hug


@hug.get()
def quick():
    return "Serving!"


if __name__ == "__main__":
    hug.API(__name__).http.serve()
