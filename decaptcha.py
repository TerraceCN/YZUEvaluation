# -*- coding: utf-8 -*-
from io import BytesIO

import numpy as np
from PIL import Image
import onnxruntime

characters = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789abdefghjmnqrtwxy"
sess = onnxruntime.InferenceSession('./urp.onnx')


def decaptcha(content: bytes) -> str:
    captcha_arr = np.array(Image.open(BytesIO(content)))
    y_pred = sess.run(None, {'input_1': [captcha_arr]})
    y = np.argmax(np.array(y_pred), axis=2)[:,0]
    return "".join([characters[i] for i in y])
