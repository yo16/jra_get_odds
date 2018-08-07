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
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, 'lxml')

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

    print(len(tag_table.find_all('tr')))
    for i, tag_tr in enumerate(tag_table.find_all('tr')):
        print(i)
        # tr２行＝１つのレース（ただし最初のtr２行は除く）
        if i<2:
            continue

        if i%2==0:
            # ２で割った余りが０の時に初期化する
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
            if not is_title:
                # raceTitle出ない場合は、j=0はスキップ(1Rとかのリンクがある)
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
            # タイトルを、全部の投票法へ設定する
            for p in race_pages:
                p['race_title1'] = race_name1
                p['race_title2'] = race_name2

            # １レースのデータをary_page_infoへ追加
            ary_page_info.extend(race_pages)
            race_pages = []     # 念のため

    return ary_page_info


def main():
    """
    全体処理
    """
    page_info = {}
    # トップページからオッズページの情報を得る
    #url, page_info = get_ods_top_page()
    url, page_info['cname'] = ('/JRADB/accessO.html', 'pw15oli00/6D')
    print('top->オッズページ')
    print('url:%s cname:%s' % (url, page_info['cname']))

    # オッズのトップページから、日にち・競馬場ごとのページの情報を得る
    #cname_sets = get_ods_page_racecourses(url, page_info)
    cname_sets = [['/JRADB/accessO.html', 
        {'cname':'pw15orl10042018020320180804/3D'}]]
    
    print('オッズページ->特定の日・競馬場')
    for cname_set in cname_sets:
        print('url:%s cname:%s' % (cname_set[0], cname_set[1]['cname']))

    cname_sets = [cname_sets[0]]

    for cname_set in cname_sets:
        #print('url:%s, cname:%s' % (cname_set['url'], cname_set['cname']))
        # 日にち・競馬場ごとのページから、レースごとの情報を得る
        cname_sets2 = get_ods_page_race(cname_set[0], cname_set[1])
        for cname_set2 in cname_sets2:
            print('url:%s, cname:%s, t1:%s, t2:%s, v:%s' % 
                (cname_set2['url'], cname_set2['cname'], 
                cname_set2['race_title1'], cname_set2['race_title2'],
                cname_set2['vote_method'])
            )


if __name__ == '__main__':
    # main
    main()
