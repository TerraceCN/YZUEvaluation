import hashlib
from io import BytesIO

from PIL import Image
import PySimpleGUI as sg

from . import s


def get_captcha() -> bytes:
    s.get('/login')
    resp = s.get('/img/captcha.jpg')
    resp.raise_for_status()
    bio = BytesIO()
    Image.open(BytesIO(resp.content)).save(bio, format='PNG')
    bio.seek(0)
    return bio.read()


def login(username: str, password: str, captcha: str) -> bool:
    resp = s.post('/j_spring_security_check', data={
        'j_username': username,
        'j_password': hashlib.md5(password.encode('ascii')).hexdigest(),
        'j_captcha': captcha
    })
    return 'errorCode' not in resp.headers.get('Location')


layout = [
    [sg.Text('用户名', (5, 1)), sg.InputText(key='username', size=(20, 1))],
    [sg.Text('密码', (5, 1)), sg.InputText(key='password', size=(20, 1), password_char='*')],
    [sg.Text('验证码', (5, 1)), sg.InputText(key='captcha', size=(20, 1))],
    [sg.Image(size=(180, 60), key='captcha_img')],
    [sg.Ok('登录'), sg.Cancel('退出')]
]
window = sg.Window('登录', layout, font=("微软雅黑", 12))


def update_captcha():
    try:
        captcha = get_captcha()
        window['captcha_img'].update(data=captcha)
    except Exception as e:
        sg.popup_error_with_traceback('获取验证码失败', e)


def show_login_window():
    window.finalize()
    update_captcha()

    flag = False
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, '退出'):
            break
        if event == '登录':
            if not values['username']:
                sg.popup('请输入用户名')
                continue
            if not values['password']:
                sg.popup('请输入密码')
                continue
            if not values['captcha']:
                sg.popup('请输入验证码')
                continue
            try:
                login_result = login(values['username'], values['password'], values['captcha'])
            except Exception as e:
                sg.popup_error_with_traceback('登录失败', e)

            if login_result:
                flag = True
                break
            else:
                sg.popup('请检查用户名、密码或验证码是否正确')
                update_captcha()
                
    window.close()
    return flag