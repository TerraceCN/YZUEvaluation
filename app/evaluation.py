import re
import time
from typing import List
from threading import Thread

from lxml import etree
import PySimpleGUI as sg

from . import s


def get_eval_token() -> str:
    index_resp = s.get('/student/teachingEvaluation/evaluation/index')
    if (token_regex := re.search(r'name="tokenValue" value="(.*?)"', index_resp.text)) is None:
        raise Exception('请先登录')
    token = token_regex.group(1)
    return token


def get_eval_list() -> List[dict]:
    resp = s.post(
        '/student/teachingEvaluation/teachingEvaluation/search',
        data={
            'optType': 1,
            'pageSize': 50
        })
    return resp.json()['data']


def get_eval_form(
    evaluatedPeople: str,
    evaluatedPeopleNumber: str,
    questionnaireCode: str,
    questionnaireName: str,
    coureSequenceNumber: str,
    evaluationContentNumber: str,
    tokenValue: str
) -> dict:
    evaluation_page = s.post(
        '/student/teachingEvaluation/teachingEvaluation/evaluationPage',
        data={
            'count': '',
            'evaluatedPeople': evaluatedPeople,
            'evaluatedPeopleNumber': evaluatedPeopleNumber,
            'questionnaireCode': questionnaireCode,
            'questionnaireName': questionnaireName,
            'coureSequenceNumber': coureSequenceNumber,
            'evaluationContentNumber': evaluationContentNumber,
            'evaluationContentContent': '',
            'tokenValue': tokenValue
        }
    )

    base_data = {
        'optType': 'submit',
        'tokenValue': tokenValue,
        'questionnaireCode': questionnaireCode,
        'evaluationContent': evaluationContentNumber,
        'evaluatedPeopleNumber': evaluatedPeopleNumber,
        'count': '',
        'zgpj': '老师上的课很好'
    }

    html = etree.HTML(evaluation_page.text)
    options = html.xpath('//tr/td/div[1]/label/input')
    if (len(options) == 0):
        raise Exception('该问卷没有选项')
    for option in options:
        base_data[option.attrib['name']] = option.attrib['value']
    
    return base_data


def submit_eval(form: dict) -> bool:
    assessment = s.post(
        '/student/teachingEvaluation/teachingEvaluation/assessment',
        data=form
    )
    return assessment.json()['result'] == 'success'


data = []
layout = [
    [sg.Table(
        data,
        headings=[
            '课程号', # id.evaluationContentNumber
            '课序号', # id.coureSequenceNumber
            '课程名', # evaluationContent
            '教师', # evaluatedPeople
            '是否已评教', # isEvaluated
        ],
        auto_size_columns=False,
        col_widths=[
            8,
            5,
            30,
            8,
            10
        ],
        justification='center',
        num_rows=10,
        key="table"
    )],
    [
        sg.Button('开始', size=(5, 1)), 
        sg.ProgressBar(0, key='progress_bar', size=(30, 30)),
        sg.Text('未开始', key='evaluating_name', size=(30, 1))
    ]
]
window = sg.Window('评教列表', layout, font=("微软雅黑", 12))


def show_evaluation_window():
    window.finalize()
    
    try:
        elist = get_eval_list()
        data = [
            [
                e['id']['evaluationContentNumber'],
                e['id']['coureSequenceNumber'],
                e['evaluationContent'],
                e['evaluatedPeople'],
                e['isEvaluated'],
            ]
            for e in elist
        ]
        window['table'].update(data)
    except Exception as e:
        sg.popup_error_with_traceback('获取评教列表失败', e)
        return

    eval_thread = None
    thread_stop = False
    

    def _start_evaluation(elist: List[dict], window: sg.Window):
        global eval_thread

        error_msg = ''

        try:
            token = get_eval_token()
        except Exception as e:
            error_msg = '获取token失败'
            window['开始'].update(disabled=False)
            sg.popup_error_with_traceback(error_msg, e)
            window['evaluating_name'].update(error_msg)
            eval_thread = None
            return

        for i, e in enumerate(elist):
            window['evaluating_name'].update(e['evaluationContent'])
            window['progress_bar'].update(i + 1)
            if e['isEvaluated'] == '是':
                continue
            try:
                form = get_eval_form(
                    evaluatedPeople=e['evaluatedPeople'],
                    evaluatedPeopleNumber=e['id']['evaluatedPeople'],
                    questionnaireCode=e['questionnaire']['questionnaireNumber'],
                    questionnaireName=e['questionnaire']['questionnaireName'],
                    coureSequenceNumber=e['id']['coureSequenceNumber'],
                    evaluationContentNumber=e['id']['evaluationContentNumber'],
                    tokenValue=token
                )
            except Exception as e:
                error_msg = '获取评教表单失败'
                window['开始'].update(disabled=False)
                sg.popup_error_with_traceback(error_msg, e)
                window['evaluating_name'].update(error_msg)
                eval_thread = None
                return

            sec = 121
            while sec > 0 and not thread_stop:
                sec -= 1
                window['evaluating_name'].update(e['evaluationContent'] + f'(等待: {sec}s)')
                time.sleep(1)
            if thread_stop:
                return 
            try:
                result = submit_eval(form)
            except Exception as e:
                error_msg = '提交评教失败'
                window['开始'].update(disabled=False)
                sg.popup_error_with_traceback(error_msg, e)
                window['evaluating_name'].update(error_msg)
                eval_thread = None
                return

            if result:
                data[i][4] = '是'
                window['table'].update(data)
            else:
                error_msg = f'{e["evaluationContent"]} 评教失败, 评教已停止'
                sg.popup_error(error_msg)
                window['evaluating_name'].update(error_msg)
                window['开始'].update(disabled=False)
                eval_thread = None
                return
        
        window['evaluating_name'].update('已完成')
        window['开始'].update(disabled=False)
        eval_thread = None

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        if event == '开始':
            if eval_thread is not None:
                sg.popup('评教已在运行')
                continue
            eval_thread = Thread(target=_start_evaluation, args=(elist, window))
            eval_thread.start()
            window['开始'].update(disabled=True)
    if eval_thread is not None:
        thread_stop = True
        eval_thread.join()
    window.close()
