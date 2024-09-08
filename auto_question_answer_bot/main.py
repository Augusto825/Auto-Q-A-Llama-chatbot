import os
import ftplib
import pandas as pd
import schedule
import time
import csv
import io
import logging
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
from config import FTP_HOST, FTP_USER, FTP_PASSWORD, WP_CONTENT_FOLDER, QUESTIONS_FOLDER, ANSWERS_FOLDER, LLAMA_MODEL


# Connect to FTP server
ftp = ftplib.FTP(FTP_HOST)
ftp.login(user=FTP_USER, passwd=FTP_PASSWORD)

def answer_question(question):
    try:
        url = 'http://localhost:3000/predict'
        data = {'question': question}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            answer = response.text
            return answer
        else:
            logging.error(f"Error generating answer: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error generating answer: {e}")
        return None

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
        logging.error(f"Error in get_questions(): {e}")
        return []

def answer_question_file(question_file):
    try:
        logging.info("Q & A bot running!")
        # Download question file
        with open(question_file, 'wb') as file:
            response = ftp.retrbinary('RETR '+ WP_CONTENT_FOLDER + QUESTIONS_FOLDER + question_file, file.write)

            if not response.startswith('226'):
                logging.error(f"Error downloading question file {question_file}: {response}")
                return

        # Read question file
        try:
            questions_df = pd.read_csv(question_file)
        except pd.errors.EmptyDataError:
            logging.error(f"Question file {question_file} is empty")
            return
        
        # Create answer file
        answer_file = question_file.replace('question-', 'answer-')
        if not os.path.exists(answer_file):
            answers_df = pd.DataFrame(columns=['ID', 'ANSWER', 'STATUS'])
            answers_df.to_csv(answer_file, index=False)

        # Answer each question using Llama model
        for index, row in questions_df.iterrows():
            if row['STATUS'] is None or row['STATUS']!= 'done':
                logging.info(f"Answering question {row['ID']}")
                question = row['QUESTION']
                answer = answer_question(question)
                if answer is not None:
                    answers_df = pd.read_csv(answer_file)
                    answers_df.loc[len(answers_df)] = [row['ID'].replace('q', 'a'), answer, 'null']
                    answers_df.to_csv(answer_file, index=False)

                    # Update question file with answer status
                    questions_df.loc[index, 'STATUS'] = 'done'
                    questions_df.to_csv(question_file, index=False)
        # Upload updated question file to FTP server
        with open(question_file, 'rb') as file:
            response = ftp.storbinary('STOR '+ WP_CONTENT_FOLDER + QUESTIONS_FOLDER + question_file, file)
            if not response.startswith('226'):
                logging.error(f"Error uploading question file {question_file}: {response}")
                return
        # Upload answer file to FTP server
        with open(answer_file, 'rb') as file:
            response = ftp.storbinary('STOR '+ WP_CONTENT_FOLDER + ANSWERS_FOLDER + answer_file, file)
            if not response.startswith('226'):
                logging.error(f"Error uploading answer file {answer_file}: {response}")
                return
        logging.info("Answered the questions once.")
    except Exception as e:
        logging.error(f"Error in answer_question({question_file}): {e}")

def monitor_questions():
    question_files = get_questions()
    for question_file in question_files:
        logging.info(f"Processing question file {question_file}")
        answer_question_file(question_file)

# Execute monitor_questions immediately
monitor_questions()

# Schedule monitor_questions to run every 1 minute
schedule.every(1).minutes.do(monitor_questions)  # Monitor every 1 minute

try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    logging.info("Monitoring stopped by user")
finally:
    if ftp is not None:
        ftp.quit()