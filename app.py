from flask import Flask, request, jsonify, session, render_template
import sqlite3
import hashlib
import base64
import numpy as np
import cv2
from deepface import DeepFace
from PIL import Image
import io
import os
from database import init_db

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_this'

#initialization
init_db()

#emotion list
EMOTION_ADVICE = {
    'happy':{'en':'Happy',
             'advice':"It's wonderful to see you in a good mood. Keep this positive energy going, and consider writing down what made you happy today so you can look back on it later."},
    'sad':{'en':'Sad',
           'advice':"Feeling sad is completely normal. Give yourself some time to heal. You might find it helpful to listen to calming music or express your thoughts in writing."},
    'angry':{'en':'Angry',
             'advice':"Take a few deep breaths and allow yourself a moment to calm down. Try to identify the cause of your anger and express it through words or journaling."},
    'fear':{'en':'Fear',
            'advice':"When you feel afraid, remind yourself that you are safe right now. Sharing your feelings with someone you trust can also help ease your fear."},
    'surprise':{'en':'Surprise',
                'advice':"Was it a pleasant surprise or a shocking moment? Either way, take a moment to process it and consider writing it down as a memorable experience."},
    'disgust':{'en':'Disgusted',
               'advice':"If something made you uncomfortable, it's okay to step back and take a break. Do something relaxing to help reset your mood."},
    'neutral':{'en':'Calm',
               'advice':"Being calm is a great state of mind. Use this peaceful moment to organize your throughts or plan your day ahead."},
}

def get_db():
    conn = sqlite3.connect('emotion_diary.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

#HomePage
@app.route('/')
def index():
    return render_template('index.html')

#Signup
@app.route('/register',methods=['POST'])
def register():
    data = request.json
    username = data.get('username','').strip()
    password = data.get('password','').strip()

    if not username or not password:
        return jsonify({'success':False,'message':"Username and password cannot be empty"})
    try:
        conn = get_db()
        conn.execute('INSERT INTO users(username, password) VALUES (?,?)',
                    (username,hash_password(password)))
        conn.commit()
        conn.close()
        return jsonify({'success':True,'message':"Login Successfully!"})
    except sqlite3.IntegrityError:
        return jsonify({'success':False,'message':"Username already exists."})
    
#Login
@app.route('/login',methods=['POST'])
def login():
    data = request.json
    username = data.get('username','').strip()
    password = data.get('password','').strip()

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username=? AND password=?',
                        (username,hash_password(password))).fetchone()
    conn.close()

    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'success':True,'username':user['username']})
    return jsonify ({'success':False,'message':"Username or password wrong"})

#Logout
@app.route('/logout', methods = ['POST'])
def logout():
    session.clear()
    return jsonify({'success':True})

#Detect emotion
@app.route('/detect', methods=['POST'])
def detect_emotion():
    if 'user_id' not in session:
        return jsonify ({'success':False,'message':"Please Sign-In First"})
    try:
        data = request.json
        image_data = data.get('image') #base64
        
        #decoding base64 pic
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        img_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        img_array = np.array(img)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        #using deepface to analyze emotion
        result = DeepFace.analyze(
            img_bgr,
            actions = ['emotion'],
            enforce_detection=False
        )

        #extract main emotions
        emotions = result[0]['emotion']
        dominant = result[0]['dominant_emotion']
        confidence = emotions[dominant]

        advice_data = EMOTION_ADVICE.get(dominant,
                                         {
                                             'en':dominant,
                                             'advice':"Keep maintaining a positive mindset! "
                                         })
        
        return jsonify({
        'success':True,
        'emotion':dominant,
        'emotion_en':advice_data['en'],
        'confidence':float(round(confidence,1)),
        'advice':advice_data['advice'],
        'all_emotions':{k:float(round(v,1)) for k, v in emotions.items()}
        })
    
    except Exception as e:
        return jsonify ({'success':False, 'message':f"Error:{str(e)}"})
    
#safe diary
@app.route('/save_diary', methods = ['POST'])
def save_diary():
    if 'user_id' not in session:
        return jsonify ({'success':False, 'message':"Please Sign-In First"})
    
    data = request.json
    emotion = data.get ('emotion','neutral')
    confidence = data.get('confidence',0)
    diary_entry = data.get('diary_entry','')

    conn = get_db()
    conn.execute(
        'INSERT INTO emotion_records (user_id, emotion, confidence, diary_entry) VALUES (?,?,?,?)',
        (session['user_id'], emotion, confidence, diary_entry)
    )
    conn.commit()
    conn.close()
    return jsonify({'success':True,'message':"Saved!"})

#History
@app.route ('/history', methods = ['GET'])
def get_history():
    if 'user_id' not in session:
        return jsonify ({'success':False,'message':"Please Sign-In First"})
    
    conn = get_db()
    records = conn.execute(
        'SELECT * FROM emotion_records WHERE user_id=? ORDER BY created_at DESC LIMIT 20',
        (session['user_id'],)
    ).fetchall()
    conn.close()

    result = []
    for r in records:
        advice_data = EMOTION_ADVICE.get(r['emotion'],{'en':r['emotion']})
        result.append({
            'id':r['id'],
            'emotion':r['emotion'],
            'emotion_en':advice_data.get('en',r['emotion']),
            'confidence':r['confidence'],
            'diary_entry':r['diary_entry'],
            'created_at':r['created_at']
        })

    return jsonify({'success':True,'records':result})

if __name__ == '__main__':
    app.run(debug=True)