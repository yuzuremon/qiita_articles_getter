import requests
import json
import configparser

# ConfigParser オブジェクトの生成
config = configparser.ConfigParser()
config.read('config.ini')
# Qiitaアカウント
QIITA_USER = config['qiita']['user']
# 投稿するslackチャンネル
SLACK_CHANNEL = config['slack']['channel']
# slackのAPIトークン
SLACK_TOKEN = config['slack']['token']
# slack投稿用URL
WEB_HOOK_URL = "https://slack.com/api/chat.postMessage"
# slack送信用のHeader
HEADERS = {
    'Content-Type' : 'application/json; charset=utf-8',
    'Authorization' : 'Bearer ' + SLACK_TOKEN
}

def get_following_tags():
    """自分がfollowしているタグの一覧を取得"""
    url = 'http://qiita.com/api/v2/users/' + QIITA_USER + '/following_tags'
    params = {'page': '1'}
    return requests.get(url, params=params).json()

def get_query(following_tags):
    """
    フォローしているタグを記事取得時の検索で使用出来るようにする
    記事取得時のqueryにtag:[タグ名]でそのタグが含まれる記事を取得出来るので、
    フォローしているタグのいずれかを含むものを取得出来るようにORでつなげていく
    """
    query = ''
    for i in range(len(following_tags)):
        query = query + 'tag:' + following_tags[i]['id'] + " OR "
    return query

def get_new_articles():
    """QiitaAPIを使用してフォローしているタグを含む新着記事を10件取得"""
    query = get_query(get_following_tags())
    url = 'http://qiita.com/api/v2/items'
    params = {'page': '1', 'per_page': '10', 'query': query.rstrip(' OR ')}
    return requests.get(url, params=params).json()

def create_attachments(new_articles):
    """取得した記事からattachmentsを生成"""
    attachments = []
    for i in range(len(new_articles)):
        # 記事のタグを取得
        tags = 'タグ：'
        for tag in new_articles[i]['tags']:
            tags = tags + '[' + tag['name'] + ']'

        # 投稿した記事をattachmentに追加
        attachments.append(
            {
                'title' : '<' + new_articles[i]['url'] + '|' + new_articles[i]['title'] + '>',  # タイトルと記事のリンク
                'text' : tags,  # 記事のタグ
                'author_name' : new_articles[i]['user']['id'],  # 投稿者名
                'author_link' : 'https://qiita.com/' + new_articles[i]['user']['id'],  # 投稿者のQiitaページへのリンク
                'author_icon' : new_articles[i]['user']['profile_image_url'],  # 投稿者のQiitaアイコン
                'footer' :  new_articles[i]['updated_at']  # 記事の投稿時間
            }
        )
    return attachments

def send_slack_title():
    """slackへ送信(スレッドタイトル)"""
    return requests.post(WEB_HOOK_URL, data = json.dumps({
        'channel': SLACK_CHANNEL,  # チャンネル
        'attachments': [{ 'title' : 'Qiita新着投稿' }],  # 通知内容
    }), headers = HEADERS).json()['ts']

def send_slack_articles(attachments, ts):
    """
    slackへ送信(スレッドタイトルに紐付けて記事をスレッド化)
    スレッドタイトルを送信した際のレスポンスの'ts'を'thread_ts'にセットすることで紐付けしている
    """
    requests.post(WEB_HOOK_URL, data = json.dumps({
        'channel': SLACK_CHANNEL,  # チャンネル
        'attachments': attachments,  # 通知内容
        'thread_ts' : ts,  # スレッドタイトルの'ts'
    }), headers = HEADERS)

# フォローしているタグを含む記事を新着で10件取得
new_articles = get_new_articles()
# スレッドのタイトルに紐付けて新着記事を送信
send_slack_articles(create_attachments(new_articles), send_slack_title())
