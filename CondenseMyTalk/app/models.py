"""
Definition of models.
"""

import numpy as np

from django.db import models
from django.conf import settings

import matplotlib.pyplot as plt

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import math

from moviepy.editor import *

import os
import cloudstorage as gcs
from google.cloud import storage

import nltk
import json
nltk.download('stopwords')
nltk.download('punkt')
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from string import punctuation
from nltk.probability import FreqDist
from heapq import nlargest
from collections import defaultdict
from wordfreq import zipf_frequency
from django.contrib.auth import get_user_model
import string
import random

def random_string_generator(size=10, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def unique_order_id_generator():
    order_new_id= random_string_generator()
    qs_exists= Video.objects.filter(videoid= order_new_id).exists()
    if qs_exists:
        return unique_order_id_generator()
    return order_new_id

# combine transcripts into one large transcript thing
def combine_json(j):
    t = ""
    for r in j:
        t += r['alternatives'][0]['transcript'] + '.'
    return t

# jsonify result to json
def jsonify(results):
    ret = []

    for result in results:
        obj = {}
        obj['alternatives'] = []
        for alternative in result.alternatives:
            d = {}
            d['transcript'] = alternative.transcript
            d['confidence'] = alternative.confidence
            word_list = []
            for word in alternative.words:
                word_list.append({
                    'start_time': {
                        'seconds': word.start_time.seconds
                    },
                    'end_time': {
                        'seconds': word.end_time.seconds
                    },
                    'word': word.word
                })
            d['words'] = word_list
            obj['alternatives'].append(d)
        ret.append(obj)
    return ret

def sanitize_input(data):
    """ 
    Currently just a whitespace remover. More thought will have to be given with how 
    to handle sanitzation and encoding in a way that most text files can be successfully
    parsed
    """
    replace = {
        ord('\f') : ' ',
        ord('\t') : ' ',
        ord('\n') : ' ',
        ord('\r') : None
    }

    return data.translate(replace)

def tokenize_content(content):
    """
    Accept the content and produce a list of tokenized sentences, 
    a list of tokenized words, and then a list of the tokenized words
    with stop words built from NLTK corpus and Python string class filtred out. 
    """
    stop_words = set(stopwords.words('english') + list(punctuation))
    words = word_tokenize(content.lower())
    
    return [
        sent_tokenize(content),
        [word for word in words if word not in stop_words]    
    ]

def score_tokens(filterd_words, sentence_tokens):
    """
    Builds a frequency map based on the filtered list of words and 
    uses this to produce a map of each sentence and its total score
    """
    word_freq = FreqDist(filterd_words)

    ranking = defaultdict(int)

    for i, sentence in enumerate(sentence_tokens):
        for word in word_tokenize(sentence.lower()):
            if word in word_freq:
                ranking[i] += word_freq[word]

    return ranking

def summarize(ranks, sentences, length):
    """
    Utilizes a ranking map produced by score_token to extract
    the highest ranking sentences in order after converting from
    array to string.  
    """
    if int(length) > len(sentences): 
        print("Error, more sentences requested than available. Use --l (--length) flag to adjust.")
        exit()

    indexes = nlargest(length, ranks, key=ranks.get)
    final_sentences = [sentences[j] for j in sorted(indexes)]
    return ' '.join(final_sentences) 



# Create your models here.
class Video(models.Model):
    name = models.CharField(max_length=500)
    uploader = models.ForeignKey(get_user_model(),
                                 on_delete=models.CASCADE)
    videoid = models.CharField(max_length = 16, primary_key=True, default=unique_order_id_generator)
    videofile = models.FileField(upload_to='videos/',
                                 null=True, verbose_name="")

    def __str__(self):
        return self.name + ": " + str(self.videofile)

    def analyse_rois(self):
        v = VideoFileClip(os.path.join(settings.MEDIA_ROOT, str(self.videofile)))
        rois = self.regionofinterest_set.all()
        graph = [0 for i in range(math.ceil(v.duration))]
        v.reader.close()
        v.audio.reader.close_proc()
        for i in rois:
            if i.positive:
                graph[i.timestamp] += 1
            else:
                graph[i.timestamp] -= 1

        total_importance = sum(graph)
        return graph


    def add_roi(self, timestamp, link, comment, positive):
        # adds a region of interest, either positive or negative, with 
        # supplemental information
        r = RegionOfInterest()
        r.video = self
        r.timestamp = timestamp
        r.link = link
        r.comment = comment
        r.positive = positive

        return r.save()

    def make_transcript(self):
        client = speech.SpeechClient()
        f = os.path.join(settings.MEDIA_ROOT,
                         os.path.splitext(str(self.videofile))[0] +
                         "_AUDIO.wav")
        audio = types.RecognitionAudio(uri='gs://condensemytalk/' + 
                      os.path.splitext(str(self.videofile))[0] + "_AUDIO.wav")
        config = types.RecognitionConfig(language_code = 'en-US',
                                enable_word_time_offsets=True)
        operation = client.long_running_recognize(config, audio)

        return operation

    def save_audio(self):
        client = speech.SpeechClient()
        f = os.path.join(settings.MEDIA_ROOT,
                         os.path.splitext(str(self.videofile))[0] +
                         "_AUDIO.wav")
        content.write_audiofile(f, codec='pcm_s16le', ffmpeg_params = ["-ac", "1"])
        storage_client = storage.Client()
        bucket = storage_client.get_bucket('condensemytalk')
        blob = bucket.blob(os.path.splitext(str(self.videofile))[0] + "_AUDIO.wav")

        blob.upload_from_filename(f)

    def summarize_full(self, t, len):
        """ Drive the process from argument to output """ 
        content = sanitize_input(t)
        sentence_tokens, word_tokens = tokenize_content(content)  
        sentence_ranks = score_tokens(word_tokens, sentence_tokens)
        return summarize(sentence_ranks, sentence_tokens, len)

    def condense(self, retention):
        f = os.path.join(settings.MEDIA_ROOT,
                         os.path.splitext(str(self.videofile))[0] +
                         "_TRANSCRIPT.txt")
        with open(f, 'r') as F:
            text = F.read()
            transcript_dict = json.loads(text)


        v = VideoFileClip(os.path.join(settings.MEDIA_ROOT, str(self.videofile)))
        L = math.ceil(v.duration)
        condensed_frames = [False for i in range(L)]
        # user summary
        R = self.analyse_rois()

        
        # text summary 
        text = combine_json(transcript_dict)
        summary = self.summarize_full(text, 10)
        for a in transcript_dict:
            l = a['alternatives'][0]['transcript'].split(' ')
            for w in range(len(l)):
                if len(l[w:]) > 5 and ' '.join(l[w:w + 5]) in summary: # part of the summary!
                    for word_object in a['alternatives'][0]['words']:
                        for j in range(word_object['start_time']['seconds'], word_object['end_time']['seconds']):
                            if zipf_frequency(word_object['word'], 'en') > 0:
                                R[j] += round(zipf_frequency('the', 'en') / zipf_frequency(word_object['word'], 'en'))
                            else:
                                R[j] += 1

        # needs retention value ratio of validated content:
        original_sum = sum(R)
        imp_percent = 0
        while float(imp_percent) / original_sum < retention:
            condensed_frames[R.index(max(R))] = True
            imp_percent += max(R)
            R[R.index(max(R))] = min(R)
        
        # expand condensed frames by padding before and after:
        padding = 4
        i = 0
        while i < L:
            if condensed_frames[i]:
                for j in range(i, max(0, i - padding), -1):
                    condensed_frames[j] = True
                for j in range(i, min(L, i + padding + 1)):
                    condensed_frames[j] = True
                i += padding + 1
            else:
                i += 1
       
        condensed_clips = []
        start_idx = 0
        while start_idx < L:
            if condensed_frames[start_idx]:
                end_idx = start_idx + 1
                while end_idx < L and condensed_frames[end_idx]:
                    end_idx += 1
                tiny_clip = v.subclip(int(start_idx), int(end_idx))
                condensed_clips.append(tiny_clip)

                start_idx = end_idx + 1
            else:
                start_idx += 1

        v.reader.close()
        v.audio.reader.close_proc()
        
        condensed_film = concatenate_videoclips(condensed_clips)
        condensed_film.write_videofile(os.path.join(settings.MEDIA_ROOT,
                                       os.path.splitext(str(self.videofile))[0] +
                                       "_CONDENSED" +
                                       os.path.splitext(str(self.videofile))[1]))

        return condensed_frames

class RegionOfInterest(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    timestamp = models.IntegerField() # time stamp in seconds of video
    link = models.URLField()
    comment = models.TextField(max_length=10000)
    positive = models.BooleanField()

    def __str__(self):
        return self.video.name + ": " + str(self.timestamp)
