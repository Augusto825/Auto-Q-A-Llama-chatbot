import os
import ftplib
import pandas as pd
import schedule
import time
import csv
import io
from llama import Llama 

# FTP settings
FTP_HOST ='malachairising.com'
FTP_USER = 'freelancer@burgerkingclaim.com'
FTP_PASSWORD = 'Freelancer2024@900AM'
FTP_PORT = 21

# WordPress settings
WP_CONTENT_FOLDER = '/wp-content/'
QUESTIONS_FOLDER = 'questions/'
ANSWERS_FOLDER = 'answers/'

# Llama settings
LLAMA_MODEL = 'llama-7b'

# Connect to FTP server
ftp = ftplib.FTP(FTP_HOST)
ftp.login(user=FTP_USER, passwd=FTP_PASSWORD)

def get_questions():
    try:
        # Get list of question files
        question_files = []
        ftp.cwd(WP_CONTENT_FOLDER + QUESTIONS_FOLDER)
        for file in ftp.nlst():
            if file.startswith('question-') and file.endswith('.csv'):
                question_files.append(file)
        return question_files
    except Exception as e:
        print(f"Error in get_questions(): {e}")

def answer_question(question_file):
    try:
        # Download question file
        ftp.retrbinary('RETR '+ WP_CONTENT_FOLDER + QUESTIONS_FOLDER + question_file, open(question_file, 'wb').write)
        
        # Read question file
        questions_df = pd.read_csv(question_file)
        
        # Answer each question using Llama model
        for index, row in questions_df.iterrows():
            if row['STATUS'] is None or row['STATUS']!= 'done':
                print("complete", row)
                answer = llama.answer(row['QUESTION'])
                # Update question file with answer
                questions_df.loc[index, 'ANSWER'] = answer
                # Update question file with answer status
                questions_df.loc[index, 'STATUS'] = 'done'
        
        # Save updated question file
        questions_df.to_csv(question_file, index=False)
        
        # Upload updated question file
        ftp.storbinary('STOR '+ WP_CONTENT_FOLDER + QUESTIONS_FOLDER + question_file, open(question_file, 'rb'))
        
        # Save answers in answer file
        answer_file = question_file.replace('question-', 'answer-')
        answers_df = questions_df[['ID', 'ANSWER', 'STATUS']]
        answers_df.to_csv(answer_file, index=False)
        
        # Upload answer file
        ftp.storbinary('STOR'+ WP_CONTENT_FOLDER + ANSWERS_FOLDER + answer_file, open(answer_file, 'rb'))
    except Exception as e:
        print(f"Error in answer_question({question_file}): {e}")

def monitor_questions():
    question_files = get_questions()
    for question_file in question_files:
        print("step1", question_file)
        answer_question(question_file)

# Execute monitor_questions immediately
monitor_questions()

# Schedule monitor_questions to run every 1 minute
schedule.every(1).minutes.do(monitor_questions)  # Monitor every 1 minute

try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    print("Monitoring stopped by user")
finally:
    if ftp is not None:
        ftp.quit()