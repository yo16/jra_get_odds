"""
JRAのページから、オッズを取得する
2018/7/28
"""
import requests
from bs4 import BeautifulSoup
import re

TOP_URL = 'http://www.jra.go.jp/'

def get_page_obj(target_url, dict_data):
    """
    url, dict_dataからページを開き、BeautifulSoupオブジェクトを返す。
    """
    # ページの情報を得る
    if (target_url is None) or (dict_data is None):
        return None
    # 先頭が/の場合は、先頭の/を取る
    if target_url[0:1] == '/':
        target_url = target_url[1:]
    
    # オッズページを開き、BeautifulSoup情報を得る
    ods_url = '%s%s' % (TOP_URL, target_url)
    r = requests.post(ods_url, data=dict_data)
    r.encoding = r.apparent_encoding   # すごく遅いから、外したいけど外すとたまにエラー
    #soup = BeautifulSoup(r.text, 'lxml')
    soup = BeautifulSoup(r.text, 'html5lib')

    return soup



def get_ods_top_page():
    """
    トップページから、オッズのページの情報を得る
    """
    top_page_url = TOP_URL
    target_url = ''
    form_info = {}

    r = requests.get(top_page_url)
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, 'lxml')

    # doActionを呼び出している部分を取得
    for tag_li in soup.find_all('li', attrs={'id':'menu1'}):
        tag_ul = tag_li.find('ul')
        for tag_li2 in tag_ul.find_all('li'):
            tag_a = tag_li2.find('a')
            if 'onclick' in tag_a.attrs:
                str_onclick = tag_a.attrs['onclick']
                #print(tag_a.text + '/' + str_onclick)
                if tag_a.text == 'オッズ':
                    m = re.match(r"doAction\('([^']+)','([^']+)'\)",
                        str_onclick)
                    if m:
                        target_url = m.group(1)
                        form_info['cname'] = m.group(2)
    if len(target_url)==0:
        return (None, None)

    """
    役割がわけわからなくなってきたので一旦コメントアウト。
    本当は要らない処理なので。。
    # formの要素を取得
    tag_form = soup.find('form', attrs={'id': 'cmmForm01'})
    for tag_input in tag_form.find_all('input'):
        input_name = tag_input.attrs['name']
        # cnameは知ってるので除く
        if input_name == 'cname':
            continue
        
        input_value = ''
        if 'value' in tag_input.attrs:
            input_value = tag_input.attrs['value']
        
        form_info[input_name] = input_value
    """

    return (target_url, form_info)


def get_ods_page_racecourses(url, page_data):
    """
    オッズのトップページから、日にち・競馬場ごとのページを見て、
    その中の各レース毎のオッズを得る。
    """
    # ページの情報を得る
    obj_xml = get_page_obj(url, page_data)

    # doActionの引数群を得る
    ods_page_parameters = []
    for tag_div in obj_xml.find_all('div', attrs={'class':'joSelectArea'}):
        for tag_a in tag_div.find_all('a', attrs={'href':'#'}):
            if 'onclick' in tag_a.attrs:
                str_onclick = tag_a.attrs['onclick']
                #print(str_onclick)
                m = re.match(r".*doAction\('([^']+)','([^']+)'\)", str_onclick)
                if m:
                    ods_page_parameters.append(
                        [m.group(1), {'cname':m.group(2)}]
                    )
    #print(ods_page_parameters)

    return ods_page_parameters


def get_ods_page_race(url, obj_param):
    """
    日にち・競馬場ごとのページから、レースごとの情報を得る
    """
    ary_page_info = []

    # ページの情報を得る
    xml = get_page_obj(url, obj_param)

    # レースごとの情報を集める
    #tag_table = xml.find('table', class_='raceList2')
    tag_table = xml.find('table', attrs={'class': 'raceList2'})

    # 日にちと競馬場の情報を取得
    tag_td_kaisaibi = xml.find('td', attrs={'class': 'kaisaibi'})
    str_kaisaibi = tag_td_kaisaibi.text
    m = re.match(r"^ *([0-9]+年[0-9]+月[0-9]+日（.）) ([0-9]+)回([^0-9]+)([0-9]+)日",
        str_kaisaibi)
    str_date = ''
    str_n_kai = ''
    str_keibajo = ''
    str_n_hi = ''
    if m:
        str_date = m.group(1)
        str_n_kai = m.group(2)
        str_keibajo = m.group(3)
        str_n_hi = m.group(4)

    for i, tag_tr in enumerate(tag_table.find_all('tr')):
        # tr２行＝１つのレース（ただし最初のtr２行は除く）
        if i<2:
            continue

        if i%2==0:
            # ２で割った余りが０の時に初期化する
            race_no = ''
            race_name1 = ''
            race_name2 = ''
            race_pages = []

        for j, tag_td in enumerate(tag_tr.find_all('td')):
            is_title = False
            if 'class' in tag_td.attrs:
                if 'raceTitleUpper' in tag_td.attrs['class']:
                    race_name1 = tag_td.text
                    is_title = True
                elif 'raceTitleLower' in tag_td.attrs['class']:
                    if tag_td.text != '\xa0':
                        race_name2 = tag_td.text
                    is_title = True
                elif 'raceNo' in tag_td.attrs['class']:
                    tag_img = tag_td.find('img')
                    race_no = tag_img.attrs['alt']
            if not is_title:
                # raceTitleでない場合は、j=0はスキップ(1Rとかのリンクがある)
                if j==0:
                    continue

                tag_a = tag_td.find('a', attrs={'href':'#'})
                if tag_a is None:
                    continue
                # このtdで１つの投票法を表している
                str_onclick = tag_a.attrs['onclick']
                m = re.match(r".*doAction\('([^']+)','([^']+)'\)", str_onclick)
                if not m:
                    continue
                url = m.group(1)
                cname = m.group(2)
                tag_img = tag_a.find('img')
                if tag_img is None:
                    continue
                str_vote_method = tag_img.attrs['alt']
                
                # race_pagesへ追加
                race_pages.append(
                    {
                        'url': url,
                        'cname': cname,
                        'vote_method': str_vote_method
                    }
                )

        if i%2==1:
            # ２で割った余りが１の時、まとめ
            # タイトル等を、全部の投票法へ設定する
            for p in race_pages:
                p['date'] = str_date
                p['n_kai'] = str_n_kai
                p['keibajo'] = str_keibajo
                p['n_hi'] = str_n_hi
                p['race_no'] = race_no
                p['race_title1'] = race_name1
                p['race_title2'] = race_name2

            # １レースのデータをary_page_infoへ追加
            ary_page_info.extend(race_pages)
            race_pages = []     # 念のため

    return ary_page_info


def get_ods_by_race(ods_pages_info):
    """
    オッズを取得する
    """
    result_ods = {
        'general': {
            'date': ods_pages_info[0]['date'],
            'n_kai': ods_pages_info[0]['n_kai'],
            'keibajo': ods_pages_info[0]['keibajo'],
            'n_hi': ods_pages_info[0]['n_hi'],
            'race_title1': ods_pages_info[0]['race_title1'],
            'race_title2': ods_pages_info[0]['race_title2']
        },
        'methods': []
    }

    # 個々のオッズページを読む
    for ods_page_info in ods_pages_info:
        one_ods = []    # oneなのに配列・・・

        # ページ情報を取得
        page_param = {'cname': ods_page_info['cname']}
        page = get_page_obj(ods_page_info['url'], page_param)

        # 販売方法ごとに異なるスクレイピングする方法で取得
        method = ods_page_info['vote_method']
        if method == '単勝複勝':
            # 単勝と複勝のオッズと、全体の情報を入手
            ods_tan, ods_fuku, general_info = get_ods_by_race_tanfuku(page)
            one_ods.append({'method': '単勝', 'ods':ods_tan})
            one_ods.append({'method': '複勝', 'ods':ods_fuku})
            
            # general_infoはここで登録する
            for k, v in general_info.items():
                result_ods['general'][k] = v

        elif method == '枠連':
            cur_ods = get_ods_by_race_wakuren(page)
            one_ods.append({
                'method': method,
                'ods': cur_ods
            })
            
        elif method == '馬連':
            cur_ods = get_ods_by_race_umaren(page)
            one_ods.append({
                'method': method,
                'ods': cur_ods
            })

        elif method == 'ワイド':
            cur_ods = get_ods_by_race_wide(page)
            one_ods.append({
                'method': method,
                'ods': cur_ods
            })

        elif method == '馬単':
            cur_ods = get_ods_by_race_umatan(page)
            one_ods.append({
                'method': method,
                'ods': cur_ods
            })

        elif method == '3連複':
            cur_ods = get_ods_by_race_3renfuku(page)
            one_ods.append({
                'method': method,
                'ods': cur_ods
            })

        elif method == '3連単':
            cur_ods = get_ods_by_race_3rentan(page)
            one_ods.append({
                'method': method,
                'ods': cur_ods
            })
        
        if len(one_ods)>0:
            result_ods['methods'].extend(one_ods)

    return result_ods


def get_ods_by_race_tanfuku(xml):
    """
    単勝複勝 のページを読み込み、オッズと、
    合わせて馬の情報等の共通情報を返す
    """
    uma_infos = []
    ods_tan = []
    ods_fuku = []

    waku_ban = 0
    tag_div_table = xml.find('div', attrs={'class': 'ozTanfukuTableUma'})
    for tag_tr in tag_div_table.find_all('tr'): # 1行＝1馬
        # 枠番は１行上と同じtr内にないことがあるので、ここで初期化しない。
        uma_ban = 0
        uma_info = {}
        ods_fuku_local = []

        for tag_th in tag_tr.find_all('th'):
            if 'waku' in tag_th.attrs['class']:
                # 枠番
                waku_ban = int(tag_th.text)
            elif 'umaban' in tag_th.attrs['class']:
                # 馬番
                uma_ban = int(tag_th.text)
        if uma_ban==0:
            continue
        for tag_td in tag_tr.find_all('td'):
            td_class = tag_td.attrs['class']
            td_text = (tag_td.text).strip()
            tag_a = tag_td.find('a')
            if tag_a is not None:
                a_text = (tag_a.text).strip()

            if 'bamei' in td_class:
                # 馬名
                uma_info['bamei'] = a_text
            elif 'oztan' in td_class:
                #　オッズ単勝
                ods_tan.append(float(td_text))
            elif 'fukuMin' in td_class:
                # オッズ複勝 最小
                ods_fuku_local.append(float(td_text))
            elif 'fukuMax' in td_class:
                # オッズ複勝 最大
                ods_fuku_local.append(float(td_text))
            elif 'seirei' in td_class:
                # 性齢
                uma_info['seibetsu'] = td_text[:1]
                uma_info['nenrei'] = int(td_text[1:])
            elif 'batai' in td_class:
                # 馬体重
                match_result = re.match(r'([0-9]+)\((.*)\)', td_text)
                uma_info['batai'] = int(match_result.group(1))
                if match_result.group(2) == '初出走':
                    uma_info['batai_zougen'] = None
                else:
                    uma_info['batai_zougen'] = int(match_result.group(2))
            elif 'futan' in td_class:
                # 負担重量
                uma_info['futan'] = float(td_text)
            elif 'kishu' in td_class:
                # 騎手
                if a_text.startswith('▲'):  # 30回以下 -3kg
                    uma_info['kisyu_minarai'] = -3.0
                    a_text = a_text[1:]
                elif a_text.startswith('△'):    # 50回以下 -2kg
                    uma_info['kisyu_minarai'] = -2.0
                    a_text = a_text[1:]
                elif a_text.startswith('☆'):    # 100回以下 -1kg
                    uma_info['kisyu_minarai'] = -1.0
                    a_text = a_text[1:]
                else:
                    uma_info['kisyu_minarai'] = 0.0
                uma_info['kishu'] = a_text
            elif 'choukyou' in td_class:
                # 調教師
                uma_info['choukyou'] = a_text

        ods_fuku.append(ods_fuku_local)

        uma_info['uma_ban'] = uma_ban
        uma_info['waku_ban'] = waku_ban

        uma_infos.append(uma_info)

    return ods_tan, ods_fuku, {'uma_info': uma_infos}


def get_ods_by_race_wakuren(xml):
    """
    枠連 のページを読み込み、オッズを得る
    """
    ods_wakuren = []

    tag_in_tables = xml.find_all('table', attrs={'class': 'ozWakuINTable'})
    for i, tag_table in enumerate(tag_in_tables):
        # １つの枠
        tag_trs = tag_table.find_all('tr')
        for j, tag_tr in enumerate(tag_trs):
            if j==0:
                continue
            # 相手の枠
            tag_th = tag_tr.find('th')
            tag_td = tag_tr.find('td', attrs={'class': 'tdoz'})
            if tag_td is not None:
                waku_info = { \
                    'no': [i+1, int(tag_th.text)], \
                    'ods': float(tag_td.text) \
                }
                
                ods_wakuren.append(waku_info)

    return ods_wakuren


def get_ods_by_race_umaren(xml):
    """
    馬連 のページを読み込み、オッズを得る
    """
    ods_umaren = []

    tag_tables = xml.find_all('table', 
        attrs={'class': 'ozUmarenUmaINTable'})
    for tag_table in tag_tables:
        tag_th_uma1 = tag_table.find('th', attrs={'class': 'title'})
        # 最初の馬番
        uma1 = tag_th_uma1.text
        tag_trs = tag_table.find_all('tr')
        for i, tag_tr in enumerate(tag_trs):
            if i==0:
                continue
            # 相手の馬番
            tag_th_uma2 = tag_tr.find('th', attrs={'class': 'thubn'})
            uma2 = tag_th_uma2.text
            tag_td_ods = tag_table.find('td', attrs={'class': 'tdoz'})
            ods = tag_td_ods.text
            uma_info = { \
                'no': [uma1, uma2], \
                'ods': ods \
            }

            ods_umaren.append(uma_info)

    return ods_umaren


def get_ods_by_race_wide(xml):
    """
    ワイド のページを読み込み、オッズを得る
    """
    ods_wide = []

    tag_tables = xml.find_all('table',
        attrs={'class': 'ozWideUmaINTable'})
    for tag_table in tag_tables:
        tag_th_uma1 = tag_table.find('th', attrs={'class': 'title'})
        # 最初の馬番
        uma1 = int(tag_th_uma1.text)
        trs = tag_table.find_all('tr')
        for i, tr in enumerate(trs):
            if i==0:
                continue
            th_uma2 = tr.find('th', attrs={'class': 'thubn'})
            td_ods_min = tr.find('td', attrs={'class': 'wideMin'})
            td_ods_max = tr.find('td', attrs={'class': 'wideMax'})
            # 相手の馬番
            uma2 = int(th_uma2.text)
            ods_min = float(td_ods_min.text)
            ods_max = float(td_ods_max.text)
            wide_info = { \
                'no': [uma1, uma2], \
                'ods': [ods_min, ods_max] \
            }
            ods_wide.append(wide_info)
    
    return ods_wide


def get_ods_by_race_umatan(xml):
    """
    馬単 のページを読み込み、オッズを得る
    """
    ods_umatan = []

    tag_tables = xml.find_all('table', 
        attrs={'class': 'ozUmatanUmaINTable'})
    for tag_table in tag_tables:
        tag_th_uma1 = tag_table.find('th', attrs={'class': 'title'})
        # 最初の馬番
        uma1 = int(tag_th_uma1.text)
        tag_trs = tag_table.find_all('tr')
        for i, tag_tr in enumerate(tag_trs):
            if i==0:
                continue
            # 相手の馬番
            tag_th_uma2 = tag_tr.find('th', attrs={'class': 'thubn'})
            uma2 = int(tag_th_uma2.text)
            tag_td_ods = tag_tr.find('td', attrs={'class': 'tdoz'})
            try:
                ods = float(tag_td_ods.text)
                uma_info = { \
                    'no': [uma1, uma2], \
                    'ods': ods \
                }
                ods_umatan.append(uma_info)
            except:
                pass
    
    return ods_umatan


def get_ods_by_race_3renfuku(xml):
    """
    3連複 のページを読み込み、オッズを得る
    """
    ods_3renfuku = []

    tag_tables = xml.find_all('table', \
        attrs={'class': 'ozSanrenUmaINTable'})
    for tag_table in tag_tables:
        tag_th_title = tag_table.find('th',
            attrs={'class': 'title'})
        title = tag_th_title.text
        uma1, uma2 = title.split('-')
        uma1 = int(uma1)
        uma2 = int(uma2)

        tag_trs = tag_table.find_all('tr')
        for tag_tr in tag_trs:
            tag_th_uma3 = tag_tr.find('th', attrs={'class': 'thubn'})
            if tag_th_uma3 is None:
                continue
            uma3 = int(tag_th_uma3.text)
            tag_td_ods = tag_tr.find('td', attrs={'class': 'tdoz'})
            try:
                ods = float(tag_td_ods.text)
                uma_info = { \
                    'no': [uma1, uma2, uma3], \
                    'ods': ods \
                }
                ods_3renfuku.append(uma_info)
            except:
                pass
    
    return ods_3renfuku


def get_ods_by_race_3rentan(xml):
    """
    3連単 のページを読み込み、オッズを得る
    """
    ods_3rentan = []

    tag_tables = xml.find_all('table', \
        attrs={'class': 'santanOddsHyo'})
    for tag_table in tag_tables:
        tag_tbody = tag_table.find('tbody', recursive=False)
        if tag_tbody is None:
            tag_trs = tag_table.find_all('tr', recursive=False)
        else:
            tag_trs = tag_tbody.find_all('tr', recursive=False)
        uma1 = 0
        uma2 = []
        for i, tag_tr in enumerate(tag_trs):
            if i==0:
                # １着
                tag_th = tag_tr.find('th', attrs={'class': 'ubn2'})
                uma1 = int(tag_th.text)
            elif i==1:
                # ２着
                tag_ths = tag_tr.find_all('th', \
                    attrs={'class': 'ubn2'})
                for tag_th in tag_ths:
                    uma2.append(int(tag_th.text))
            else:
                # ３着
                tag_td_uma2s = tag_tr.find_all('td', \
                    attrs={'class': 'jikubetuOdds'})
                for j, tag_td_uma2 in enumerate(tag_td_uma2s):
                    tag_trs_uma3s = tag_td_uma2.find_all('tr')
                    for tag_tr_uma3 in tag_trs_uma3s:
                        tag_th_uma3 = tag_tr_uma3.find('th', \
                            attrs={'class': 'ubn3'})
                        uma3 = int(tag_th_uma3.text)
                        try:
                            tag_td_odds = tag_tr_uma3.find('td', \
                                attrs={'class': 'oddsData'})
                            ods = float(tag_td_odds.text)
                            uma_info = {
                                'no': [uma1, uma2[j], uma3],
                                'ods': ods
                            }
                            ods_3rentan.append(uma_info)
                        except:
                            pass
                
    return ods_3rentan
    

def main():
    """
    全体処理
    """
    page_info = {}
    # トップページからオッズページの情報を得る
    print('top->オッズページ')
    url, page_info = get_ods_top_page()
    #url, page_info['cname'] = ('/JRADB/accessO.html', 'pw15oli00/6D')
    #print('url:%s cname:%s' % (url, page_info['cname']))

    # オッズのトップページから、日にち・競馬場ごとのページの情報を得る
    print('オッズページ->特定の日・競馬場')
    cname_sets = get_ods_page_racecourses(url, page_info)
    #cname_sets = [['/JRADB/accessO.html', {'cname':'pw15orl10042018020520180811/CA'}]]
    #for cname_set in cname_sets:    # 1ループ＝1日の1競馬場
    #    print('url:%s cname:%s' % (cname_set[0], cname_set[1]['cname']))

    ary_result = []
    for cname_set in cname_sets:    # 1ループ＝1レース
        #print('url:%s, cname:%s' % (cname_set['url'], cname_set['cname']))
        # 日にち・競馬場ごとのページから、レースごとの情報を得る
        print('特定の日・競馬場->１レース')
        cname_sets2 = get_ods_page_race(cname_set[0], cname_set[1])
        for cname_set2 in cname_sets2:  # 1ループ＝１販売方法
            print('url:%s, cname:%s, t1:%s, t2:%s, R:%s, v:%s' % 
                (cname_set2['url'], cname_set2['cname'], 
                cname_set2['race_title1'], cname_set2['race_title2'],
                cname_set2['race_no'], cname_set2['vote_method'])
            )
    
        # オッズ情報を取得する
        print('１レース->発売方法*n')
        ods_info = get_ods_by_race(cname_sets2)
        ary_result.append(ods_info)

        
########################################################

def test_get_ods_by_race_tanfuku():
    """
    単勝、複勝オッズ取得のテスト
    """
    tanfuku = [{
        'url': '/JRADB/accessO.html',
        'cname': 'pw151ou1004201802050120180811Z/6B',
        'race_title1': '2歳未勝利（混合）［指定］',
        'race_title2': '',
        'vote_method': '単勝複勝',
        'date': '2018年8月11日（土）',
        'n_kai': '2',
        'keibajo': '新潟',
        'n_hi': '5'
    }]
    ods_tan, ods_fuku, gen_info = get_ods_by_race(tanfuku)
    print(ods_tan)
    print(ods_fuku)
    print(gen_info)

def test_get_ods_by_race_wakuren():
    """
    枠連オッズ取得のテスト
    """
    wakuren = [{
        'url': '/JRADB/accessO.html',
        'cname': 'pw153ouS304201802070120180818Z/4A',
        'race_title1': '2歳未勝利牝［指定］',
        'race_title2': '',
        'vote_method': '枠連',
        'date': '2018年8月18日（土）',
        'n_kai': '2',
        'keibajo': '新潟',
        'n_hi': '7'
    }]
    ods_wakuren = get_ods_by_race(wakuren)
    print(ods_wakuren)

def test_get_ods_by_race_umaren():
    """
    馬連オッズ取得のテスト
    """
    umaren = [{
        'url': '/JRADB/accessO.html',
        'cname': 'pw154ouS304201802071220180818Z/D5',
        'race_title1': '歳以上500万下（混合）［指定］',
        'race_title2': '',
        'vote_method': '馬連',
        'date': '2018年8月18日（土）',
        'n_kai': '2',
        'keibajo': '新潟',
        'n_hi': '7'
    }]
    ods = get_ods_by_race(umaren)
    print(ods)

def test_get_ods_by_race_wide():
    """
    ワイドオッズ取得のテスト
    """
    umaren = [{
        'url': '/JRADB/accessO.html',
        'cname': 'pw155ouS304201802071220180818Z/59',
        'race_title1': '3歳以上500万下（混合）［指定］',
        'race_title2': '',
        'vote_method': 'ワイド',
        'date': '2018年8月18日（土）',
        'n_kai': '2',
        'keibajo': '新潟',
        'n_hi': '7'
    }]
    ods = get_ods_by_race(umaren)
    print(ods)

def test_get_ods_by_race_umatan():
    """
    馬単 オッズ取得のテスト
    """
    umaren = [{
        'url': '/JRADB/accessO.html',
        'cname': 'pw156ouS304201802071220180818Z/DD',
        'race_title1': '3歳以上500万下（混合）［指定］',
        'race_title2': '',
        'vote_method': '馬単',
        'date': '2018年8月18日（土）',
        'n_kai': '2',
        'keibajo': '新潟',
        'n_hi': '7'
    }]
    ods = get_ods_by_race(umaren)
    print(ods)

def test_get_ods_by_race_3renfuku():
    """
    3連複 オッズ取得のテスト
    """
    umaren = [{
        'url': '/JRADB/accessO.html',
        'cname': 'pw157ouS304201802071220180818Z99/C3',
        'race_title1': '3歳以上500万下（混合）［指定］',
        'race_title2': '',
        'vote_method': '3連複',
        'date': '2018年8月18日（土）',
        'n_kai': '2',
        'keibajo': '新潟',
        'n_hi': '7'
    }]
    ods = get_ods_by_race(umaren)
    print(ods)

def test_get_ods_by_race_3rentan():
    """
    3連単 オッズ取得のテスト
    """
    umaren = [{
        'url': '/JRADB/accessO.html',
        'cname': 'pw158ou1004201802071220180818Z/1F',
        'race_title1': '3歳以上500万下（混合）［指定］',
        'race_title2': '',
        'vote_method': '3連単',
        'date': '2018年8月18日（土）',
        'n_kai': '2',
        'keibajo': '新潟',
        'n_hi': '7'
    }]
    ods = get_ods_by_race(umaren)
    print(ods)


if __name__ == '__main__':
    # main
    main()
    #test_get_ods_by_race_tanfuku()
    #test_get_ods_by_race_wakuren()
    #test_get_ods_by_race_umaren()
    #test_get_ods_by_race_wide()
    #test_get_ods_by_race_umatan()
    #test_get_ods_by_race_3renfuku()
    #test_get_ods_by_race_3rentan()

    print('end')
