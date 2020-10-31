class Camera(object):
    @staticmethod
    def start():
        return "4276"

    @staticmethod
    def stop():
        return "4277"

    @staticmethod
    def move(speed, rotation):
        return "6600{}{}64000099".format("00" if speed == -100 else format(100 + speed, "x"), format(100+rotation, "x"))

    @staticmethod
    def jump():
        return "6605646464000099"

    @staticmethod
    def ping():
        return "6600646464000099"
