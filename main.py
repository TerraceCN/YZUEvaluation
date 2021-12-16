# -*- coding: utf-8 -*-
import httpx
from lxml import etree

from decaptcha import decaptcha

username = input('请输入学号: ')
password = input('请输入密码: ')

client = httpx.Client()
captcha_content = client.get("http://jw1.yzu.edu.cn/validateCodeAction.do").content
login_result = client.post(f"http://jw1.yzu.edu.cn/loginAction.do",
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
pj_list = client.get('http://jw1.yzu.edu.cn/jxpgXsAction.do?oper=listWj&wjbz=null')
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
print('未评教')
for d in no:
    print(f'\t{d[4]} {d[2]}')
confirm = input('请核对信息，如信息无误请输入Y开始一键评教[y/N]: ')
if confirm != 'Y' and confirm != 'y':
    print('操作取消')
    exit(0)

for d in no:
    page = client.post('http://jw1.yzu.edu.cn/jxpgXsAction.do',
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
                 'zgpj': r'%C0%CF%CA%A6%BA%DC%B0%F4'})
    result = client.post('http://jw1.yzu.edu.cn/jxpgXsAction.do?oper=wjpg',
                         data=data)
    if '评估成功' in result.text:
        print(f'{d[4]} 评教成功!')
    else:
        print(f'{d[4]} 评教失败，返回信息如下：')
        print(result.text)
        exit(1)
