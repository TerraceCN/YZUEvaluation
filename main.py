# -*- coding: utf-8 -*-
import os
import time
import traceback

import httpx
from lxml import etree

from decaptcha import decaptcha

try:
    username = input('请输入学号: ')
    password = input('请输入密码: ')

    hosts = ['jw1.yzu.edu.cn', 'jw2.yzu.edu.cn', 'jw3.yzu.edu.cn']
    best_host = None
    best_resp_time = 9999999999
    print('正在选择最优服务器')
    for h in hosts:
        t = 0
        try:
            for _ in range(10):
                stime = time.time()
                resp = httpx.get(f'http://{h}/validateCodeAction.do', timeout=5)
                etime = time.time()
                t += int((etime - stime) * 1000)
        except httpx.HTTPError:
            print(f'{h} 响应超时')
            continue
        if resp.status_code != 200:
            print(f'{h} 响应失败')
            continue
        resp_time = t / 10
        print(f'{h} 平均响应时间: {resp_time}ms')
        if best_resp_time > resp_time:
            best_resp_time = resp_time
            best_host = h
    assert best_host, '当前网络状况不佳，建议稍后再试'
    print(f'已选择 {best_host} 作为当前服务器')

    client = httpx.Client()
    captcha_content = client.get(f"http://{best_host}/validateCodeAction.do").content
    login_result = client.post(f"http://{best_host}/loginAction.do",
                            data={"zjh1": "",
                                    "tips": "",
                                    "lx": "",
                                    "evalue": "",
                                    "eflag": "",
                                    "fs": "",
                                    "dzslh": "",
                                    "zjh": username,
                                    "mm": password,
                                    "v_yzm": decaptcha(captcha_content)})
    assert "学分制综合教务" in login_result.text, '登陆失败，请检查用户名和密码'

    print('正在获取评教列表')
    pj_list = client.get(f'http://{best_host}/jxpgXsAction.do?oper=listWj&wjbz=null')
    html = etree.HTML(pj_list.text)
    yes = []
    no = []
    for pj in html.xpath('//table[@id="user"]/tr'):
        status = pj.xpath('./td')[3].text == '是'
        data = pj.xpath('./td[last()]/img')[0].attrib['name'].split('#@')
        if status:
            yes.append(data)
        else:
            no.append(data)

    print(f'获取数据成功，共 {len(no)} 门课需要评教')
    print('已评教:')
    for d in yes:
        print(f'\t{d[4]} {d[2]}')
    print('未评教:')
    for d in no:
        print(f'\t{d[4]} {d[2]}')
    confirm = input('请核对信息，如信息无误请输入Y开始一键评教[y/N]: ')
    assert confirm == 'Y' or confirm == 'y', '操作取消'

    for d in no:
        page = client.post(f'http://{best_host}/jxpgXsAction.do',
                        data={'wjbm': d[0],
                                'bpr': d[1],
                                'pgnr': d[5],
                                'oper': 'wjShow',
                                'wjmc': d[3],
                                'bprm': d[2],
                                'pgnrm': d[4],
                                'wjbz': 'null',
                                'pageSize': '20',
                                'page': '1',
                                'currentPage': '1',
                                'pageNo': ''})
        page_html = etree.HTML(page.content.decode('gbk', errors='ignore'))
        questions = page_html.xpath('//table[@id="tblView"]/tr/td/table/tr/td/input[1]')
        data = {}
        for q in questions:
            data[q.attrib['name']] = q.attrib['value']
        data.update({'wjbm': d[0],
                    'bpr': d[1],
                    'pgnr': d[5],
                    'xumanyzg': 'zg',
                    'wjbz': '',
                    'zgpj': '%C0%CF%CA%A6%BA%DC%B0%F4'})
        result = client.post(f'http://{best_host}/jxpgXsAction.do?oper=wjpg',
                            data=data)
        assert '评估成功' in result.text, f'{d[4]} 评教失败，返回信息如下:\n{result.text}'
        print(f'{d[4]} 评教成功!')
except KeyboardInterrupt:
    print('操作取消')
    os.system('pause')
except Exception as e:
    raise e
