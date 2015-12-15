import requests
import cv2
import time
import configparser
import uuid
from boto3.session import Session


class Alarm:
    def __init__(self, config):
        self.config = config

    def trigger(self):
        img_url = self.upload_2_s3(self.config['aws'], self.config['s3'])
        self.pushover_send(self.config['pushover'],
                           'Alert',
                           'Motion detected!\n<a href="{}">IMG</a>'.format(img_url))

    @staticmethod
    def pushover_send(pushover_config, title, msg):
        """
        Send push notification via PushOver service
        :param pushover_config:
        :param title:
        :param msg:
        """
        pushover_config.update({'title': title, 'message': msg, 'html': 1})
        print(requests.post("https://api.pushover.net/1/messages.json", data=pushover_config).json())

    @staticmethod
    def upload_2_s3(aws_config, s3_config):
        """
        Upload img to AWS S3
        :param aws_config:
        :param s3_config:
        :return: image url
        """
        session = Session(**aws_config)

        img_name = str(uuid.uuid4()) + ".jpg"

        s3 = session.resource('s3')
        s3.meta.client.upload_file('img.jpg', s3_config['bucket'], img_name, ExtraArgs={'ACL': 'public-read'})

        img_url = 'https://s3-{}.amazonaws.com/{}/{}'.format(aws_config['region_name'], s3_config['bucket'], img_name)

        return img_url


def get_image():
    camera = cv2.VideoCapture(0)
    return_value, image = camera.read()
    del camera
    cv2.imwrite("img.jpg", image)

    return cv2.imread("img.jpg", 1)


def save_image(file, image_matrix):
    cv2.imwrite(file, image_matrix)


def bw_average(image_matrix):
    return image_matrix[:, :, 0]


# parsing 'ini' config to dictionary
config = configparser.RawConfigParser()
config.read("lconf.ini")
conf = {}

for section in config.sections():
    conf[section] = {}
    for pair in config.items(section):
        key, value = pair
        conf[section][key] = value

# main program section
history = []
alarm = Alarm(conf)
while True:
    try:
        img_old = img
        img = get_image()
    except:
        img_old = get_image()
        time.sleep(1)
        img = get_image()

    history.append((img_old - img).mean())
    avg = sum(history) / len(history)
    delta = abs(history[-1] - avg)
    print(delta)

    max_delta = 3

    if delta > max_delta:
        alarm.trigger()

    time.sleep(0.5)
