import os
import sys
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__)))
os.chdir(os.path.realpath(os.path.dirname(__file__)))


# from pydotenv import load_dotenv
from tweepy import Stream
from tweepy import OAuthHandler
from tweepy.streaming import StreamListener
import json
from datetime import datetime
import sqlite3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from unidecode import unidecode
import time
from threading import Lock, Timer
from helpers import _remove_ascii_emojis_and_extra_spaces, log_error, db_cleanup
import pandas as pd
from stopwrds import stop_words
import regex as re
from collections import Counter
import string
import pickle
import itertools
from textblob import TextBlob
from dotenv import load_dotenv   #for python-dotenv method
load_dotenv()   


filterHMs_ = [
    'Erica #BBNaija', 'Kiddwaya #BBNaija', 'Neo #BBNaija', 'Vee #BBNaija', 'Brighto #BBNaija',
    'Eric #BBNaija', 'Praise #BBNaija', 'Prince #BBNaija', 'Nengi #BBNaija', 'Laycon #BBNaija',
    'Tolanibaj #BBNaija', 'Tochi #BBNaija', 'TrikyTee #BBNaija', 'Ozo #BBNaija', 'Dorathy #BBNaija',
    'Wathoni #BBNaija', 'Lucy #BBNaija', 'Kaisha #BBNaija'
]

filterHMs = [
    'Erica', 'Kiddwaya', 'Neo', 'Vee', 'Brighto',
    'Eric', 'Praise', 'Prince', 'Nengi', 'Laycon',
    'Tolanibaj', 'Tochukwu', 'TrikyTee', 'Ozo', 'Dorathy',
    'Wathoni', 'Lucy', 'Kaisha']

analyzer = SentimentIntensityAnalyzer()


CUSTOMER_KEY=os.environ.get('TWITTER_CONSUMER_KEY')
CUSTOMER_SECRET=os.environ.get('TWITTER_CONSUMER_SECRET')
ACCESS_TOKEN=os.environ.get('TWITTER_ACCESS_TOKEN_KEY')
ACCESS_SECRET=os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

print(CUSTOMER_KEY, CUSTOMER_SECRET)
# isolation lever disables automatic transactions,
# we are disabling thread check as we are creating connection here, but we'll be inserting from a separate thread (no need for serialization)
conn = sqlite3.connect('bbntwitterxy.db', isolation_level=None, check_same_thread=False)
# connection = engine.raw_connection()
cursor = conn.cursor()

def create_table():
    try:
        cursor.execute("PRAGMA journal_mode=wal")
        cursor.execute("PRAGMA wal_checkpoint=TRUNCATE")

        # changed unix to INTEGER (it is integer, sqlite can use up to 8-byte long integers)
        cursor.execute("CREATE TABLE IF NOT EXISTS sentiment(id INTEGER PRIMARY KEY AUTOINCREMENT, unix INTEGER, tweet TEXT, place VARCHAR, sentiment REAL)")
        # key-value table for random stuff
        cursor.execute("CREATE TABLE IF NOT EXISTS misc(key TEXT PRIMARY KEY, value TEXT)")
        # id on index, both as DESC (as you are sorting in DESC order)
        cursor.execute("CREATE INDEX id_unix ON sentiment (id DESC, unix DESC)")
        # make an interface to the main db; saving space
        cursor.execute("CREATE VIRTUAL TABLE sentiment_fts USING fts5(tweet, place, content=sentiment, content_rowid=id, prefix=1, prefix=2, prefix=3)")
        cursor.execute("""
            CREATE TRIGGER sentiment_insert AFTER INSERT ON sentiment BEGIN
                INSERT INTO sentiment_fts(rowid, tweet, place) VALUES (new.id, new.tweet, new.place);
            END
            """)
    except Exception as e:
        print(str(e))

create_table()

lock = Lock()

class CustomListener(StreamListener):
    data = []
    lock = None

    def __init__(self, lock):
        #set lock
        self.lock = lock

        # init timer for database save
        self.save_in_database()

        # call init of StramListener
        super().__init__()

    def save_in_database(self):
        #set a timer (1 second)
        Timer(1, self.save_in_database).start()

        # with lock, if there's data, save in transaction using one bulk query
        with self.lock:
            if len(self.data):

                now = datetime.now()
                if now.hour == 1 and now.minute == 45 and now.second <= 10:
                    KEEP_DATA = 7.5
                    cur_time_ms = time.time()*1000
                    one_day = 84600 * 1000
                    del_to = int(cur_time_ms - (KEEP_DATA * 1000))
                    sql = "DELETE FROM sentiment WHERE unix < '{}'".format(del_to)
                    c.execute(sql)
                    time.sleep(5)
                    sql = 'VACCUM'
                    c.execute(sql)
                    time.sleep(5)
                    db_cleanup(datetime.now(), msg="SUCCESS")
                # else:
                #     db_cleanup(datetime.now(), msg="NOT TIME")

                cursor.execute('BEGIN TRANSACTION')
                try:
                    cursor.executemany("INSERT INTO sentiment (unix, tweet, place, sentiment) VALUES (?, ?, ?, ?)", self.data)
                except:
                    pass
                cursor.execute('COMMIT')

                self.data = []

    def on_data(self, data):
        try:
            #print('data')
            data = json.loads(data)

            # there are records like that:
            # {'limit': {'track': 14667, 'timestamp_ms': '1520216832822'}}
            for housemate in filterHMs_:
                if housemate.split(' ')[0].lower() in data['text'].lower():

                    if 'truncated' not in data:
                        return True
                    if data['truncated']:
                        tweet = unidecode(_remove_ascii_emojis_and_extra_spaces(data['extended_tweet']['full_text']))
                    else:
                        tweet = unidecode(_remove_ascii_emojis_and_extra_spaces(data['text']))

                    # if "RT" not in tweet or "whatsapp" not in tweet.lower(): #filter RTS and potential spam
                    
                    if data["user"]["location"]:
                        place = data["user"]["location"]
                    elif data["user"]["location"] == "Nigeria":
                        place = '<N/A>, Nigeria'
                    elif data["user"]["location"] == "Lagos":
                        place = 'Lagos, Nigeria'
                    # elif 'Earth' in data["user"]["location"]:
                    #     place = 'Earth'
                    else:
                        if data["user"]["location"] == "" or data["user"]["location"] == " ":
                            place = 'NOT PROVIDED'
                        else:
                            place = 'NOT PROVIDED'
                    time_ms = data['timestamp_ms']
                    sentiment = analyzer.polarity_scores(tweet)['compound']
                        # print("==============")
                        # print("APPENDING: ",tweet)
                        # print("================")
                    with self.lock:
                        self.data.append((time_ms, tweet, place, sentiment))
                        print(self.data)
                    #print(time_ms, tweet, sentiment)

                    # append to data list (to be saved every 1 second)
                    # print(tweet)
                    # tweet = [tweet for tweets in self.data["tweet"] if tweet not tweets]]
                    
                    # if "RT" not in tweet or "whatsapp" in tweet.lower(): #filter RTS and potential spam


                # else:
                #     print("HOUSEMATE NOT FOUND", housemate)
        
        except KeyError as e:
            #print(data)
            print(str(e))
        return True

    def on_error(self, status):
        print(status)


# make a counter with blacklist words and empty word with some big value - we'll use it later to filter counter
stop_words.append('')
blacklist_counter = Counter(dict(zip(stop_words, [1000000] * len(stop_words))))

# complie a regex for split operations (punctuation list, plus space and new line)
punctuation = [str(i) for i in string.punctuation]
split_regex = re.compile("[ \n" + re.escape("".join(punctuation)) + ']')

def map_nouns(col):
    return [word[0] for word in TextBlob(col).tags if word[1] == u'NNP']

# generate "trending"
def generate_trending():
    try:
        # select last 10k tweets
        df = pd.read_sql("SELECT * FROM sentiment ORDER BY id DESC, unix DESC LIMIT 10000", conn)
        df['nouns'] = list(map(map_nouns,df['tweet']))

        # make tokens
        tokens = split_regex.split(' '.join(list(itertools.chain.from_iterable(df['nouns'].values.tolist()))).lower())
        # clean and get top 10
        trending = (Counter(tokens) - blacklist_counter).most_common(10)

        # get sentiments
        trending_with_sentiment = {}
        for term, count in trending:
            df = pd.read_sql("SELECT sentiment.* FROM  sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 1000", conn, params=(term,))
            trending_with_sentiment[term] = [df['sentiment'].mean(), count]

        # save in a database
        with lock:
            cursor.execute('BEGIN TRANSACTION')
            try:
                cursor.execute("REPLACE INTO misc (key, value) VALUES ('trending', ?)", (pickle.dumps(trending_with_sentiment),))
            except:
                pass
            cursor.execute('COMMIT')


    except Exception as e:
        log_error(str(e))

    finally:
        Timer(5, generate_trending).start()

Timer(1, generate_trending).start()

while True:
    try:
        auth = OAuthHandler(CUSTOMER_KEY, CUSTOMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
        twitterStream = Stream(auth, CustomListener(lock))
        twitterStream.filter(track=filterHMs_)
    except Exception as e:
        print(str(e))
        time.sleep(5)
