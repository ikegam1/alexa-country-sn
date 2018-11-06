from chalice import Chalice
import logging
import json
import random
import re
import os
import sys

app = Chalice(app_name='alexa-country-sn')
logger = logging.getLogger()
debug = os.environ.get('DEBUG_MODE')
if debug == '1':
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.ERROR)

#quiz
import names

#mp3
drumrole_mp3 = "soundbank://soundlibrary/musical/amzn_sfx_drum_and_cymbal_01"
question_mp3 = "soundbank://soundlibrary/ui/gameshow/amzn_ui_sfx_gameshow_bridge_02"
correct_mp3 = "soundbank://soundlibrary/ui/gameshow/amzn_ui_sfx_gameshow_positive_response_01"
incorrect_mp3 = "soundbank://soundlibrary/ui/gameshow/amzn_ui_sfx_gameshow_negative_response_01"


class BaseSpeech:
    def __init__(self, speech_text, should_end_session, session_attributes=None, reprompt=None):
 
        """
        引数:
            speech_text: Alexaに喋らせたいテキスト
            should_end_session: このやり取りでスキルを終了させる場合はTrue, 続けるならFalse
            session_attributes: 引き継ぎたいデータが入った辞書
            reprompt:
        """
        if session_attributes is None:
            session_attributes = {}

        self._response = {
            'version': '1.0',
            'sessionAttributes': session_attributes,
            'response': {
                'outputSpeech': {
                    'type': 'SSML',
                    'ssml': '<speak>'+speech_text+'</speak>'
                },
                'shouldEndSession': should_end_session,
            },
        }

        if reprompt is None:
           pass
        else:
           """リプロンプトを追加する"""
           self._response['response']['reprompt'] = {
                'outputSpeech': {
                    'type': 'SSML',
                    'ssml': '<speak>'+reprompt+'</speak>'
                }
           }

        self.speech_text = speech_text
        self.should_end_session = should_end_session
        self.session_attributes = session_attributes

    def build(self):
        return self._response
 
 
class OneSpeech(BaseSpeech):
    """1度だけ発話する(ユーザーの返事は待たず、スキル終了)"""
 
    def __init__(self, speech_text, session_attributes=None):
        super().__init__(speech_text, True, session_attributes)
 
 
class QuestionSpeech(BaseSpeech):
    """発話し、ユーザーの返事を待つ"""
 
    def __init__(self, speech_text, session_attributes=None, reprompt=None):
        super().__init__(speech_text, False, session_attributes, reprompt)

 
@app.lambda_function()
def default(event, context):
    logger.info(json.dumps(event))
    request = event['request']
    request_type = request['type']
    session = {}
    if 'session' in event:
        session = event['session']
    if request_type == 'LaunchRequest':
        return wellcomeIntent()
    elif request_type == 'IntentRequest' and 'intent' in request:
        return in_intent(request, session) 

def in_intent(request, session):
    intent = request['intent']
    logger.info(str(intent))

    if intent['name'] == 'WellcomeIntent':
        return wellcomeIntent()
    elif intent['name'] == 'AMAZON.HelpIntent':
        return helpIntent()
    elif intent['name'] == 'AMAZON.NavigateHomeIntent':
        return helpIntent()
    elif intent['name'] == 'AMAZON.StopIntent':
        return finishIntent()
    elif intent['name'] == 'AMAZON.CancelIntent':
        return finishIntent()

    if 'attributes' not in session:
        pass
    elif 'current' not in session['attributes']:
        pass
    elif session['attributes']['current'] != 'quizIntent':
        return wellcomeIntent()
    elif session['attributes']['current'] == 'quizIntent':
        return answerIntent(intent, session)

    if intent['name'] == 'QuizIntent':
        return quizIntent(session)
    elif intent['name'] == 'AnswerIntent':
        return answerIntent(intent, session)

    return fallback()

def wellcomeIntent():
    return QuestionSpeech('国名の漢字へようこそ！<emphasis level="moderate">クイズはじめる</emphasis>と言ってみてください。漢字一文字の国名がどれだけわかるかのクイズです。',{},'クイズはじめると言ってみてくださいね。終わる時は終わると言ってください。').build()

def helpIntent():
    return QuestionSpeech('漢字一文字の国名がどれだけ読めるかのクイズです。<emphasis level="moderate">クイズはじめる</emphasis>と言うとクイズをはじめられます。答えを言うと正解か不正解かを答えるよ。次の問題へ進むときは<emphasis level="moderate">次のクイズ</emphasis>と言ってくださいね').build()

def quizIntent(session):
    text = 'ではクイズです。30秒以内で答えてくださいね。<break time="1s"/>'
    text += '<audio src="%s" />' % question_mp3

    """quizcsv"""
    csv = ''
    for q in names.quiz:
       csv += u'%s,,%s\n' % (q["a"],q["w"])
    #logger.info(csv)

    quiz = random.choice(names.quiz)
    logger.info(str(quiz))
    
    text += quiz["q"]
    text += '<break time="0.5s" /> %s' % quiz["q"]
    text += '<break time="10s"/>あと10秒です。<break time="7s"/>さん。<break time="1s"/>にい。<break time="1s"/>いち。<break time="1s"/>'

    text2 = 'もう一度だけ問題を言いますよ。'
    text2 += quiz["q"]
    text2 += '<break time="1s"/>さん。<break time="1s"/>にい。<break time="1s"/>いち。<break time="1s"/>'
    logger.info(text)
    logger.info(text2)

    session_attributes = {"quiz":quiz,"current":"quizIntent"}
    return QuestionSpeech(text, session_attributes,text2).build()

def answerIntent(intent, session):
    logger.info(str(intent))
    logger.info(str(session))
    answer = ''
    try:
        quiz = session["attributes"]["quiz"]
        slots = intent['slots']
        if 'value' in slots['answerSlot']:
            answer = slots['answerSlot']['value']
        elif 'value' in slots['notanswerSlot']:
            answer = slots['notanswerSlot']['value']
    except Exception as e:
        if 'quiz' in session["attributes"]:
            session_attributes = {"quiz":quiz,"current":"quizIntent"}
            return fallback(session_attributes) 
        else:
            return fallback() 

    try:
        if 'value' in slots['answerSlot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]:
            answer = slots['answerSlot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name']
    except Exception as e:
        logger.info( "[x] Type: {type}".format(type=type(e)))
        logger.info( "[x] Error: {error}".format(error=e))

    logger.info(answer)
    text = '正解は<break time="0.5s"/>'
    text += '<audio src="%s" />' % drumrole_mp3

    if re.compile("^%s" % quiz['a']).search(answer):
        text += u'<audio src="%s" />' % correct_mp3
        text += u'<prosody rate="105%"><prosody volume="+1dB">正解は' + quiz['a'] + 'です！すごいですね！</prosody></prosody>'
        text += u'次の問題もやるときは<emphasis level="moderate">次のクイズ</emphasis>と言ってください'

    else:
        text += u'<audio src="%s" />' % incorrect_mp3
        text += u'<prosody rate="105%"><prosody volume="+1dB">ざあ<prosody pitch="+5%">んね<prosody pitch="+5%">ん</prosody>！</prosody></prosody></prosody>'
        text += u'<break time="0.5s" />正解は<emphasis level="moderate">'+quiz['a']+'</emphasis>でした'
        text += u'<break time="0.5s" />次の問題もやるときは<emphasis level="moderate">次のクイズ</emphasis>と言ってください'

    return QuestionSpeech(text, {}).build()

def finishIntent():
    return OneSpeech('遊んでくれてありがとう！またやってくださいね。').build()

def fallback(session_attribute={}):
    ssml = []
    ssml.append('すみません。聞き取れませんでした。もう一度お願いします。')
    ssml.append('もう一度お願いします。<emphasis level="moderate">はじめから</emphasis>というと最初に戻れます')
    ssml.append('ハッキリと聞き取れなかったです。もう一度言ってみて。')
    return QuestionSpeech(random.choice(ssml),session_attribute).build()



