from __future__ import print_function

import os
import sys
import json
import time
import nltk
import time
import tweepy
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def analyze_tweet(tweet):
    """Analyze the provided tweet; count personal pronouns and calculate
    sentiment.
    Args:
        tweet (obj) - tweepy tweety object.
    Returns:
        data (dict) - count of personal pronouns, sentiment calc., date, and
                      full text.
    """
    # -- Tag text.
    tokenized = nltk.word_tokenize(tweet["full_text"])
    tagged = nltk.pos_tag(tokenized)
    prp_count = len([tag for tag in tagged if tag[1] == "PRP"])
    # -- Sentiment analysis of the tweet.
    analyzer = SentimentIntensityAnalyzer()
    sentiment = analyzer.polarity_scores(tweet["full_text"])
    # -- Create data dict.
    data = {"tagged_text": tagged, "personal_pronouns": prp_count,
            "sentiment": sentiment}
    return data


class Members(object):
    def __init__(self, key, congress=115):
        """Use Probulica API to get all current representatives' information.
        Args:
            key (str) - propublica key.
            congress (int; str) - which congress to scrape.
        """
        self.congress = congress
        self.url = "https://api.propublica.org/congress/v1/{}/{}/members.json"
        # -- Collect house and senate members.
        self.rhouse = requests.get(self.url.format(congress, "house"), headers={"X-API-Key": key})
        self.rsenate = requests.get(self.url.format(congress, "senate"), headers={"X-API-Key": key})
        # -- Combine house and senate members, and add object for President and
        # -- Vice President.
        self.data = (json.loads(self.rhouse.content)["results"][0]["members"] +
                     json.loads(self.rsenate.content)["results"][0]["members"] +
                     [{"twitter_account": "mike_pence"}] +
                     [{"twitter_account": "realDonaldTrump"}])


class Tweets(object):
    def __init__(self, user, keys):
        """Scrape twitter users tweets.
        Args:
            user (str) - user name.
            keys (dict) - twitter keys.
        """
        self.user = user
        # -- Authorize twitter API.
        auth = tweepy.OAuthHandler(keys["consumer_key"], keys["consumer_secret"])
        auth.set_access_token(keys["access_token"], keys["access_token_secret"])
        api = tweepy.API(auth)
        # -- Scrape and save tweets to data attr.
        self.data = list(tweepy.Cursor(api.user_timeline,
                         screen_name="@{}".format(user),
                         tweet_mode="extended").items())
        # -- Only keep json content.
        self.data = [tweet._json for tweet in self.data]
        # -- For each tweet, analyze, and add to json.
        for tweet in self.data:
            tweet["analysis"] = analyze_tweet(tweet)


if __name__ == "__main__":
    # -- Grab keys.
    twitter = eval(os.environ["twitter_keys"])
    propub = os.environ["PROPUBKEY"]
    # -- Collect members of congress.
    print("Collecting congress data.")
    sys.stdout.flush()
    members = Members(propub)
    # -- For each member of congress...
    for ii, member in enumerate(members.data):
        tstart = time.time()
        user = member["twitter_account"]
        scraped_users = [fname[:-5] for fname in os.listdir("data")]
        # -- Check if a member of congress has a twitter account and if it's
        # -- been previously scraped.
        if (user != None) & (user not in scraped_users):
            try:
                # -- Print status.
                print("Scraping: {:40} ({}/{})                                   " \
                    .format(user, ii + 1, len(members.data)))
                sys.stdout.flush()
                # -- Append tweets to each members object.
                member["tweets"] = Tweets(user, twitter).data
                member["collected_tweets"] = time.ctime()
                # -- Save to file.
                with open("./data/{}.json".format(user), "w") as outfile:
                    json.dump(dict(member), outfile)
            except:
                print("ERROR: {}".format(user))
            # -- Prevent hitting rate limit.
            if 61 - (time.time() - tstart) > 0:
                time.sleep(61 - (time.time() - tstart))
