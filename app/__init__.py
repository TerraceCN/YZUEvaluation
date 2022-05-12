import httpx

s = httpx.Client(
    base_url='http://58.192.130.156',
    headers={
        'Host': 'ydjwxs.yzu.edu.cn'
    }
)

from . import login, evaluation


def start():
    login_result = login.show_login_window()
    if login_result:
        evaluation.show_evaluation_window()
