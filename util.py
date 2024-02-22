#!/usr/bin/env python3
# encoding: utf-8

import inspect
import re
import sys
import time
import csv
import json
from datetime import datetime, timedelta
from importlib import reload as _reload

try:
    from tqdm import tqdm
    import requests
except Exception:
    pass

CURRENT_MOD = sys.modules[__name__]
CURRENT_FILE = CURRENT_MOD.__file__

def ts2dt(ts, fmt='%Y-%m-%d %H:%M:%S'):
    '''时间戳转时间字符串，兼容不同精度(ms/s)
    命令行下也可使用date 命令：
        Mac: date -r <秒时间戳>
        Linux: date -d @<秒时间戳>
        '''
    ts = int(ts)
    if ts > 1e11:
        ts /= 1000
    return datetime.fromtimestamp(ts).strftime(fmt)


def dt2ts(dt):
    '''日期字符串转时间戳，需包含年月日时分秒，兼容不同格式'''
    dt = re.sub('\D+', ' ', dt).strip()
    return datetime.strptime(dt, '%Y %m %d %H %M %S').timestamp()


def reload(mod=CURRENT_MOD):
    return _reload(mod)


def save_func(func, dest=CURRENT_MOD, need_reload=True):
    '''将函数保存到源码中，适用于交互环境'''
    src = inspect.getsource(func)
    with open(dest.__file__, 'r+')as f:
        f.seek(0)
        orig = f.read()
        foot_idx = orig.find('\nif __name__ ==')  # 查找源码底部的__main__ 入口
        f.seek(0)
        f.write(orig[:foot_idx] + '\n' + src + '\n' + orig[foot_idx:])
    print('saved %s to %s' % (func, dest.__file__))
    need_reload and reload(dest)


def comm(path_l, mod, path_r):
    '''usage: utils.py comm a.txt <op> b.txt
    op: - only in a
        + in a or in b
        ^ both in a and b'''
    l, r = set(), set()
    with open(path_l)as f:
        for line in f:
            l.add(line.strip())
    with open(path_r)as f:
        for line in f:
            r.add(line.strip())

    if mod == '-':
        return l - r
    if mod == '+':
        return l | r
    if mod == '^':
        return l & r


def rm_url_param(url, params=[]):
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    p = urlparse(url)
    q = parse_qs(p.query)
    for k in params:
        q.pop(k, None)
    np = p._replace(query=urlencode(q, doseq=True))
    return urlunparse(np)


def extract(dom, rule):
    if isinstance(dom, str):
        from lxml import etree
        dom = etree.HTML(dom)
    if isinstance(dom, list):
        return [extract(d, rule) for d in dom]
    def _cast(k, v):
        '''key sample: key、list<str> key、list<int> key、int key、float key、str key '''
        type_name = k.split(' ', 1)
        name = type_name[-1]
        if len(type_name) == 1:
            return name, v
        if type_name[0].startswith('list<'):
            ele_type = getattr(__builtins__, type_name[0][5:-1])
            return [ele_type(i) for i in v]
        ele_type = getattr(__builtins__, type_name[0])
        if ele_type is str:
            return name, ''.join(v)
        for i in filter(None, v):   # int、 float...
            return name, ele_type(i)
    if isinstance(rule, str):
        return dom.xpath(rule)
    if isinstance(rule, dict):
        if rule.get('list_path'):
            return extract(dom.xpath(rule.pop('list_path')), rule)
        return dict(_cast(k, extract(dom, v)) for k, v in rule.items())


def run(func, args, num=20):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num) as e:
        for res in e.map(func, args):
            yield res


def first(it):
    for i in it:
        return i


def uniq(it, key=str):
    ex = set()
    res = []
    for i in it:
        k = key(i)
        if k not in ex:
            res.append(i)
        ex.add(k)
    return res


def load(path):
    if path.endswith('.csv'):
        with open(path)as f:
            head, data = None, []
            r = csv.reader(f)
            for row in r:
                if not head:
                    head = row
                    continue
                data.append(dict(zip(head, row)))
            return data
    if path.endswith('.json') or path.endswith('.ndjson'):
        return [json.loads(l,strict=0) for l in open(path)]
    return [l.strip() for l in open(path)]



def dump(data, path, head=[]):
    if path.endswith('.json'):
        from collections import Iterable
        if (isinstance(data, list) and isinstance(first(data), dict) or
                not isinstance(data, (list, dict, str)) and isinstance(data, Iterable)):
            with open(path, 'w')as f:
                for d in data:
                    f.write(json.dumps(d, ensure_ascii=0) + '\n')
        else:
            with open(path, 'w')as f:
                f.write(json.dumps(data, ensure_ascii=0, indent=2))
        return
    if path.endswith('.xlsx'):
        import pandas as pd
        return pd.DataFrame(data).to_excel(path, header=True, index=False)
    with open(path, 'w')as f:
        w = csv.writer(f)
        if head:
            w.writerow(head)
        for row in data:
            if isinstance(row, dict):
                if not head:
                    head = list(row.keys())
                    w.writerow(head)
                row = [row.get(h) for h in head]
            w.writerow(row)


class chrome:
    driver = None

    @classmethod
    def init(cls, *args):
        from selenium.webdriver.chrome.options import Options
        from selenium import webdriver
        options = Options()
        for a in args:
            options.add_argument(a)
        cls.driver = webdriver.Chrome(options=options)

    @classmethod
    def get(cls, url, rule={}, interval=0):
        if not cls.driver:
            cls.init()
        cls.driver.get(url)
        time.sleep(interval)
        html = cls.driver.page_source
        res = {'html': html, 'url': url}
        res.update(extract(html, rule))
        return res


if __name__ == '__main__':
    args = sys.argv
    if len(sys.argv) < 2:
        print('usage: util.py <command> [arg1 ...]')
        exit(1)
    try:
        comm = eval(args[1])
    except Exception:
        print('command %s not found' % sys.argv[1])
    comm = globals()[args[1]]
    if len(args) == 3 and args[2] in ['-h', '--help', 'help']:
        print(comm.__doc__)
        exit(0)
    res = globals()[args[1]](*args[2:])
    if isinstance(res, (list, tuple, set)):
        for i in res:
            print(i)
    if isinstance(res, str):
        print(res)
    if isinstance(res, int):
        exit(res)