#!/usr/bin/env python3

import re
import os
import sys
import json
import requests

from copy import deepcopy
from requests.exceptions import ConnectionError
from collections import OrderedDict


kc3_seasonal_suffixs = []

with open('./config.json', 'r', encoding='utf-8') as fp:
    config = json.load(fp)
    kc3_seasonal_suffixs = config['kc3_seasonal_suffixs']


def print_help():
    print('「kcwiki_quotes.py 使用帮助」\n')
    print('>> python kcwiki_quotes.py --fetch\n?> 获取最新的季节性语音、通常语音以及最新的quotes.json和quotes_size.json\n')
    print('>> python kcwiki_quotes.py --repair\n?> 修复kcwiki的季节性语音的WikiText\n')
    print('>> python kcwiki_quotes.py --update\n?> 更新quotes.json文件\n')
    print('* 遇到Error请不要慌张，注意读报错再做判断！ *')


def kcwiki_tutorial():
    print('「kcwiki 重命名文件教程」\n')
    print('1. 登录Kcwiki账号')
    print('2. 点击 https://zh.kcwiki.org/wiki/Special:替换文本')
    print('3. 搜索名空间点击 "（主）" 和 "File" 选项')
    print('4. 勾选 "仅在页面内容中替换" 和 "可能的话，在页面名称中替换"')
    print('5. 点击 "继续"')
    print('6. 进入新页面，去掉 "重定向至新标题时保留旧标题" 选项')
    print('7. 点击 "替换"按钮')
    print('* 谢谢你的工作让kcwiki更好！ *')


name2VoiceId = {
    'Intro': 1, 'Sec1': 2, 'Sec2': 3, 'Sec3': 4, 'ConstComplete': 5,
    'DockComplete': 6, 'Return': 7, 'Achievement': 8, 'Equip1': 9, 'Equip2': 10,
    'DockLightDmg': 11, 'DockMedDmg': 12, 'FleetOrg': 13, 'Sortie': 14, 'Battle': 15,
    'Atk1': 16, 'Atk2': 17, 'NightBattle': 18, 'LightDmg1': 19, 'LightDmg2': 20,
    'MedDmg': 21, 'Sunk': 22, 'MVP': 23, 'Proposal': 24, 'LibIntro': 25,
    'Equip3': 26, 'Resupply': 27, 'SecWed': 28, 'Idle': 29, '0000': 30,
    '0100': 31, '0200': 32, '0300': 33, '0400': 34, '0500': 35,
    '0600': 36, '0700': 37, '0800': 38, '0900': 39, '1000': 40,
    '1100': 41, '1200': 42, '1300': 43, '1400': 44, '1500': 45,
    '1600': 46, '1700': 47, '1800': 48, '1900': 49, '2000': 50,
    '2100': 51, '2200': 52, '2300': 53
}

id2Desc = {
    1: 'Intro', 2: 'Poke(1)', 3: 'Poke(2)', 4: 'Poke(3)', 5: 'Construction',
    6: 'Repair', 7: 'Return', 8: 'Ranking', 9: 'Equip(1)', 10: 'Equip(2)',
    11: 'Docking(1)', 12: 'Docking(2)', 13: 'Join', 14: 'Sortie', 15: 'Battle',
    16: 'Attack', 17: 'Yasen(2)', 18: 'Yasen(1)', 19: 'Damaged(1)', 20: 'Damaged(2)',
    21: 'Damaged(3)', 22: 'Sunk', 23: 'MVP', 24: 'Wedding', 25: 'Library',
    26: 'Equip(3)', 27: 'Supply', 28: 'Married', 29: 'Idle', 30: 'H0000',
    31: 'H0100', 32: 'H0200', 33: 'H0300', 34: 'H0400', 35: 'H0500',
    36: 'H0600', 37: 'H0700', 38: 'H0800', 39: 'H0900', 40: 'H1000',
    41: 'H1100', 42: 'H1200', 43: 'H1300', 44: 'H1400', 45: 'H1500',
    46: 'H1600', 47: 'H1700', 48: 'H1800', 49: 'H1900', 50: 'H2000',
    51: 'H2100', 52: 'H2200', 53: 'H2300'
}

desc2Id = {}

for k, v in id2Desc.items():
    desc2Id[v] = str(k)


def pre_subtitles(subtitles):
    res = {}
    for shipId in subtitles:
        res[shipId] = {}
        for voice in subtitles[shipId]:
            res[shipId][str(voice['voiceId'])] = voice['zh']
    return res


def update_subtitles():
    subtitles = {}
    quotes = {}
    with open('./quotes.json', 'r', encoding='utf-8') as fp:
        quotes = json.load(fp)
    with open('./subtitles.json', 'r', encoding='utf-8') as fp:
        subtitles = json.load(fp)
    for ship_id, voices in subtitles.items():
        s_id = str(ship_id)
        if type(voices) != dict:
            continue
        if s_id not in quotes:
            quotes[s_id] = {}
        for voice_id, content in voices.items():
            v_id = int(voice_id)
            if v_id > 53:
                continue
            content = content.strip()
            quotes[s_id][id2Desc[v_id]] = content
    with open('./quotes.json', 'w', encoding='utf-8') as fp:
        json.dump(quotes, fp, ensure_ascii=False,
                  indent=2)


def fetch_data():
    print('[-] 正在获取最新的数据……')
    session = requests.Session()
    subtitles_url = 'http://api.kcwiki.org/subtitles/detail'
    quotes_size_url = 'https://raw.githubusercontent.com/KC3Kai/KC3Kai/master/src/data/quotes_size.json'
    quotes_url = 'https://raw.githubusercontent.com/KC3Kai/kc3-translations/master/data/scn/quotes.json'
    seasonal_url = 'https://zh.kcwiki.org/index.php?title=%E8%88%B0%E5%A8%98%E7%99%BE%E7%A7%91:%E8%AF%AD%E9%9F%B3%E5%AD%97%E5%B9%95&action=raw'
    kcdata_url = 'https://kcwikizh.github.io/kcdata/ship/all.json'
    try:
        subtitles = session.get(subtitles_url).json()
        with open('./subtitles.json', 'w', encoding='utf-8') as fp:
            json.dump(pre_subtitles(subtitles), fp, ensure_ascii=False)
        print('[1] subtitles.json 获取成功！')
        quotes_size = session.get(quotes_size_url).json()
        with open('./quotes_size.json', 'w', encoding='utf-8') as fp:
            json.dump(quotes_size, fp, ensure_ascii=False)
        print('[2] quotes_size.json 获取成功！')
        quotes = session.get(quotes_url).json()
        with open('./quotes.json', 'w', encoding='utf-8') as fp:
            json.dump(quotes, fp, ensure_ascii=False, indent=2)
        print('[3] quotes.json 获取成功！')
        seasonal = session.get(seasonal_url).text
        with open('./seasonal.txt', 'w', encoding='utf-8') as fp:
            fp.write(seasonal)
        print('[4] seasonal.txt 获取成功！')
        kcdata = session.get(kcdata_url).json()
        with open('./kcdata.json', 'w', encoding='utf-8') as fp:
            json.dump(kcdata, fp, ensure_ascii=False)
        print('[5] kcdata.json 获取成功！')
    except ConnectionError:
        print('不要慌，只是网络问题，重试就好了！')
    finally:
        session.close()
    print('[Y] 全部数据获取成功！')


def update_seasonal():
    wikiId2apiId = {}
    quotes = {}
    quotes_size_json = {}
    kcdata_json = []
    with open('./kcdata.json', 'r', encoding='utf-8') as fp:
        kcdata_json = json.load(fp)
    for ship in kcdata_json:
        wikiId2apiId[ship['wiki_id']] = ship['id']
    voice_datajson = {}
    suff_data = {}
    with open('./seasonal.txt', 'r', encoding='utf-8') as fp:
        line = fp.readline()
        cur_shipid = None
        cur_voiceid = None
        while line:
            _line = line.strip()
            if not _line:
                line = fp.readline()
                continue
            if '档名' in _line:
                wiki_id, voice_type, suff = arch2tuple(_line.split()[-1])
                cur_voiceid = name2VoiceId[voice_type]
                cur_shipid = wikiId2apiId[wiki_id]
                s_id = str(cur_shipid)
                v_id = str(cur_voiceid)
                if s_id not in voice_datajson:
                    voice_datajson[s_id] = {}
                if s_id not in suff_data:
                    suff_data[s_id] = {}
                suff_data[s_id][v_id] = suff
            elif '中文译文' in _line:
                if not cur_shipid:
                    line = fp.readline()
                    continue
                translation = line.split('=')[-1].strip()
                s_id = str(cur_shipid)
                v_id = str(cur_voiceid)
                if v_id not in voice_datajson[s_id]:
                    voice_datajson[s_id][v_id] = translation
                cur_shipid = None
                cur_voiceid = None
            line = fp.readline()

    with open('./quotes.json', 'r', encoding='utf-8') as fp:
        quotes = json.load(fp)

    with open('./quotes_size.json', 'r', encoding='utf-8') as fp:
        quotes_size_json = json.load(fp)

    for api_id, voices in voice_datajson.items():
        if api_id not in quotes_size_json:
            continue
        qv_keys = quotes_size_json[api_id].keys()
        for v_id, content in voices.items():
            if v_id in qv_keys:
                seasonal_keys = list(quotes_size_json[api_id][v_id].values())
                desc = id2Desc[int(v_id)]
                _content = content.strip()
                suff = suff_data[api_id][v_id]
                for v_key in seasonal_keys:
                    if desc in quotes[api_id] and quotes[api_id][desc] == _content:
                        continue
                    if v_key and suff.find(v_key) != -1:
                        vid_seasonal = '{}@{}'.format(
                            v_id, v_key)
                        quotes[api_id][vid_seasonal] = _content

    with open('quotes.json', 'w', encoding='utf-8') as fp:
        json.dump(quotes, fp, ensure_ascii=False,
                  indent=2)


arch_pattern = re.compile(r'([0-9a-z]+)-([0-9A-Za-z]+)')


def arch2tuple(arch_name):
    arch_name_groups = re.match(arch_pattern, arch_name)
    if not arch_name_groups:
        return None, None, None
    wiki_id = arch_name_groups.group(1)
    voice_type = None
    suffix = None
    file_name = arch_name_groups.group(2)
    for v_type in name2VoiceId.keys():
        if file_name.startswith(v_type):
            voice_type = v_type
            suffix = file_name.replace(voice_type, '')
            break
    return wiki_id, voice_type, suffix


def check_suffix(suffix):
    if not suffix:
        return True
    for sf in kc3_seasonal_suffixs:
        if suffix.startswith(sf):
            return False
    return True


def trim_num(arch_name):
    while arch_name[-1].isdigit():
        arch_name = arch_name[:-1]
    return arch_name


def select_handle(arch_name):
    suffix_names = json.dumps(kc3_seasonal_suffixs, indent=2)
    suffix = arch2tuple(arch_name)[2]
    if check_suffix(suffix):
        print('!! > "{}" 不在 \n{} 之中可能无法生成文件'.format(suffix, suffix_names))
        select = input('是否删除后缀数字?[Y/N]').lower()
        if select == 'y':
            new_arch_name = trim_num(arch_name)
            print('\n{} ~> {} 修改成功！'.format(arch_name, new_arch_name))
            return new_arch_name
    select = input('是否修改档名?[Y/N]').lower()
    if not select or select != 'y':
        return arch_name
    print('可供选择的季节性后缀有\n{}\n'.format(suffix_names))
    new_arch_name = input('请输入新的档名: ')
    new_wiki_id, new_voice_tyoe, new_suffix = arch2tuple(new_arch_name)
    while check_suffix(new_suffix):
        new_arch_name = input(
            '["档名"] = "{}"\n请重试: \n{}\n请输入新的档名: '.format(arch_name, suffix_names))
        new_wiki_id, new_voice_tyoe, new_suffix = arch2tuple(new_arch_name)
    print('\n{} ~> {} 修改成功！'.format(arch_name, new_arch_name))
    return '{}-{}{}'.format(new_wiki_id, new_voice_tyoe, new_suffix)


def repair_subtitles():
    flag = False
    log = open('./repair.log', 'w', encoding='utf-8')
    suffix_table = {}
    subtitle_pattern = re.compile(r'{{台词翻译表\|type=seasonal\s*([\s\S]+?)\s*}}')
    subtitle_idx = 0
    with open('./seasonal.txt', 'r', encoding='utf-8') as fpr:
        seasonal_txt = fpr.read()
        all_subtitles = subtitle_pattern.findall(seasonal_txt)
        for subtitle in all_subtitles:
            subtitle_idx += 1
            _subtitle = '\n["编号"] = "{}"\n'.format(str(subtitle_idx).zfill(3))
            arch_name = ''
            subtitle_info = {}
            for sub_line in subtitle.split('\n'):
                line = sub_line.lstrip(' |').strip().split('=')
                attr = line[0].strip()
                value = line[1].strip()
                subtitle_info[attr] = value
                if attr == '档名':
                    arch_name = value
                _subtitle += '["{}"] = "{}"\n'.format(attr, value)
            print(_subtitle)
            new_arch_name = select_handle(arch_name)
            subtitle_info['档名'] = new_arch_name
            if new_arch_name != arch_name:
                flag = True
                log.write('No.{} "{}" ~> "{}"\n'.format(
                    str(subtitle_idx).zfill(3), arch_name, new_arch_name))
                log.flush()
                seasonal_txt = seasonal_txt.replace(arch_name, new_arch_name)
            suffix = arch2tuple(new_arch_name)[2]
            if suffix not in suffix_table:
                suffix_table[suffix] = []
            suffix_table[suffix].append(subtitle_info)
            with open('./seasonal.txt', 'w', encoding='utf-8') as fpw:
                fpw.write(seasonal_txt)
    log.close()
    if flag:
        print('WikiText发生了改变:')
        print('./repair.log >\n')
        with open('./repair.log', 'r', encoding='utf-8') as fp:
            print(fp.read())
        print('请上传至 https://zh.kcwiki.org/index.php?title=舰娘百科:语音字幕')
        print('需要替换kcwiki文本！')
        kcwiki_tutorial()


def minify_all():
    quotes = {}
    kcdata_json = []
    with open('./kcdata.json', 'r', encoding='utf-8') as fp:
        kcdata_json = json.load(fp)
    with open('./quotes.json', 'r', encoding='utf-8') as fp:
        quotes = json.load(fp)
    quotes2 = deepcopy(quotes)
    for ship_info in kcdata_json:
        ship_id = str(ship_info['id'])
        if ship_id not in quotes:
            continue
        _ship_info = ship_info
        while _ship_info['after_ship_id']:
            after_ship_id = _ship_info['after_ship_id']
            next_id = str(after_ship_id)
            for voice_desc, content in quotes[ship_id].items():
                v_id = None
                if voice_desc in desc2Id.keys():
                    v_id = desc2Id[voice_desc]
                elif '@' in voice_desc:
                    v_id = voice_desc.split('@')[0]
                if next_id in quotes:
                    for voice_desc2, content2 in quotes[next_id].items():
                        v2_id = None
                        if voice_desc2 in desc2Id.keys():
                            v2_id = desc2Id[voice_desc2]
                        elif '@' in voice_desc2:
                            v2_id = voice_desc2.split('@')[0]
                        if ship_id != next_id and v_id == v2_id and content == content2:
                            quotes2[next_id].pop(voice_desc2)
            _ship_info = kcdata_json[after_ship_id]
    with open('./quotes.json', 'w', encoding='utf-8') as fp:
        json.dump(quotes2, fp, ensure_ascii=False,
                  indent=2)


def update_data():
    print('[-] 正在更新数据……')
    update_subtitles()
    print('[1] 更新通常语音翻译成功！')
    update_seasonal()
    print('[2] 更新季节性语音翻译成功！')
    print('[Y] 语音翻译数据更新成功！')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_help()
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == '--fetch':
        fetch_data()
    elif cmd == '--update':
        update_data()
    elif cmd == '--repair':
        repair_subtitles()
    else:
        print_help()
