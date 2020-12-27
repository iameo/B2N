#2BN

This hosted the sentiment analysis on the just concluded BBN show(2020). It also served as a means of "predicting" who gets evicted using a metric score(lower the positive sentiments + **magic** == possible eviction)


The project code was private until now(27/12/2020) but hosted publicly on https://bbnsents.live (now down; DigitalOcean and name.com)



This project tapped from SentDex' sentiment analysis web app and was referenced on my web app.


### HOW TO RUN

- clone repo
- cd into repo
- command: pip install -r requirements.txt
- split terminal.
  command I: python twitter_stream.py (responsible for collecting live tweets; TWITTER API STREAMING)
  command II: python dev_server.py (to run app on server)



### NB:
I've decided to include the DBs with stored data so that could be used to fill up the web app on local server. Also, you can extract the tweets for other (NLP) projects.

I MIGHT refactor later on but to run the code successfully now just use the above guide (HOW TO RUN)
