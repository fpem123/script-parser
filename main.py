'''
    Name: app.py
    Writer: Hoseop Lee, Ainizer
    Rule: Flask app
    update: 21.01.28
'''
from flask import Flask, request, jsonify, render_template, send_file, Response

from queue import Queue, Empty
from threading import Thread
from werkzeug.utils import secure_filename
import time
import json
import csv
import os
import io

app = Flask(__name__)

requests_queue = Queue()
BATCH_SIZE = 1
CHECK_INTERVAL = 0.1

# csv 파싱 길이제한 늘림
csv.field_size_limit(100000000)

UPLOAD_FOLDER = './data/upload'
RESULT_FOLDER = './data/result'

if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

if not os.path.isdir(RESULT_FOLDER):
    os.mkdir(RESULT_FOLDER)


def handle_requests_by_batch():
    while True:
        request_batch = []

        while not (len(request_batch) >= BATCH_SIZE):
            try:
                request_batch.append(requests_queue.get(timeout=CHECK_INTERVAL))
            except Empty:
                continue

            for requests in request_batch:
                file_type = requests['input'].pop(0)

                if file_type == 'csv':
                    if len(requests['input']) == 1:
                        requests["output"] = csv_heading_parser(requests['input'][0])
                    elif len(requests['input']) == 3:
                        requests["output"] = csv_script_parser(requests['input'][0], requests['input'][1], requests['input'][2])
                elif file_type == 'json':
                    if len(requests['input']) == 1:
                        requests["output"] = json_heading_parser(requests['input'][0])
                    elif len(requests['input']) == 3:
                            requests["output"] = json_script_parser(requests['input'][0], requests['input'][1], requests['input'][2])


handler = Thread(target=handle_requests_by_batch).start()


def json_heading_parser(json_file):
    # 입력받은 파일 저장
    filename = secure_filename(json_file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    json_file.save(input_path)
    try:
        try:
            with open(input_path, 'r', encoding='latin-1') as f:
                json_data = json.load(f)
        except:
            with open(input_path, 'r', encoding='latin-1') as f:
                json_data = [json.loads(line) for line in f]

        for idx, data in enumerate(json_data):
            if idx == 0:
                line = list(data.items())
                result = [[], []]

                for i in line:
                    result[0].append(i[0])

                    text = str(i[1])
                    text = text[:30] + '...' if len(text) > 50 else text

                    result[1].append(text)

                os.remove(input_path)

                return result, 200
    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)

        return jsonify({'error': e}), 400


def json_script_parser(json_file, name_idx, dialog_idx):

    # 입력받은 파일 저장
    filename = secure_filename(json_file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    json_file.save(input_path)

    filename = filename.split('.')[0] + '.txt'
    result_path = os.path.join(RESULT_FOLDER, filename)
    try:
        try:
            with open(input_path, 'r', encoding='latin-1') as f:
                json_data = json.load(f)
        except:
            with open(input_path, 'r', encoding='latin-1') as f:
                json_data = [json.loads(line) for line in f]

        with open(result_path, 'w', encoding='utf-8') as r:
            for idx, line in enumerate(json_data):
                # 이름이 없으면 Narrator 로 셋팅
                who = " ".join(str(line[name_idx]).split()) if line[name_idx] else 'Narrator'
                dialog = " ".join(str(line[dialog_idx]).split())

                if dialog == '':
                    continue

                r.write(who + ': ' + dialog + '\n')

        # 바이너리 정보로 전송하기 위함
        with open(result_path, 'rb') as r:
            data = r.read()

        # 보안을 위한 정보 삭제
        os.remove(input_path)
        os.remove(result_path)

        # heading_parser 와 다른 형태로 전송할 것이므로 구분을 위해 fake 를 추가함
        return send_file(io.BytesIO(data), mimetype='text/plain', attachment_filename=filename), 200
       #return io.BytesIO(data), filename, 'fake'
    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)

        if os.path.exists(result_path):
            os.remove(result_path)

        return jsonify({'error': e}), 400


# CSV 파일의 meta 정보를 파싱
def csv_heading_parser(csv_file):
    # 입력받은 파일 저장
    filename = secure_filename(csv_file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    csv_file.save(input_path)

    try:
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            rdr = csv.reader(f)

            csv_headings = next(rdr)    # 컬럼 정보
            first_line = next(rdr)      # 첫째 줄 샘플

            for i in range(len(first_line)):
                first_line[i] = first_line[i][:50] + '...' if len(first_line[i]) > 30 else first_line[i]

            result = [csv_headings, first_line]

        os.remove(input_path)

        return result, 200
    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)

        return jsonify({'error': e}), 400


# csv 파일의 이름 인덱스와 대사 인덱스를 받아와서 스크립트 파일을 만듬
def csv_script_parser(csv_file, name_idx, dialog_idx):
    # 입력받은 파일 저장
    filename = secure_filename(csv_file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    csv_file.save(input_path)

    filename = filename.split('.')[0] + '.txt'
    result_path = os.path.join(RESULT_FOLDER, filename)

    try:
        name_idx = int(name_idx)
        dialog_idx = int(dialog_idx)

        if name_idx < 0 or dialog_idx < 0:
            raise Exception

        with open(input_path, 'r', encoding='utf-8-sig') as f:
            rdr = csv.reader(f)

            with open(result_path, 'w', encoding='utf-8') as r:

                for idx, line in enumerate(rdr):
                    if idx == 0:
                        pass
                    else:
                        # 이름이 없으면 Narrator 로 셋팅
                        who = " ".join(str(line[name_idx]).split()) if line[name_idx] else 'Narrator'
                        dialog = " ".join(str(line[dialog_idx]).split())

                        if dialog == '':
                            continue

                        r.write(who + ': ' + dialog + '\n')

        # 바이너리 정보로 전송하기 위함
        with open(result_path, 'rb') as r:
            data = r.read()

        # 보안을 위한 정보 삭제
        os.remove(input_path)
        os.remove(result_path)

        # heading_parser 와 다른 형태로 전송할 것이므로 구분을 위해 fake 를 추가함
        return send_file(io.BytesIO(data), mimetype='text/plain', attachment_filename=filename), 200
        #return io.BytesIO(data), filename, 'fake'
    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)

        if os.path.exists(result_path):
            os.remove(result_path)

        return jsonify({'error': e}), 400


@app.route('/<file_types>/<types>', methods=['POST'])
def csv_req(file_types, types):
    try:
        if types not in ['heading', 'script']:
            return jsonify({'message': 'Error. Wrong types'}), 400

        if requests_queue.qsize() > BATCH_SIZE:
            return jsonify({'Error': 'Too Many Requests'}), 429

        args = [file_types]
        file = request.files['file']
        args.append(file)

        if types == 'script':
            name = request.form['name']
            dialog = request.form['dialog']

            args.append(name)
            args.append(dialog)

    except Exception as e:
        return jsonify({'error': e}), 400

    req = {"input": args}
    requests_queue.put(req)

    while 'output' not in req:
        time.sleep(CHECK_INTERVAL)

    result = req['output']

    return result

'''
    if len(result) == 2:
        return jsonify(result), 200
    elif len(result) == 3:
        return send_file(result[0], mimetype='text/plain', attachment_filename=result[1]), 200
    else:
        return result
'''

# 샘플 다운로드 링크
@app.route('/csv/sample_download')
def send_csv_sample():
    return send_file('data/sample.csv', mimetype='text/csv', attachment_filename='sample.csv'), 200


@app.route('/json/sample_download')
def send_json_sample():
    return send_file('data/sample.csv', mimetype='text/csv', attachment_filename='sample.csv'), 200


##
# Sever health checking page.
@app.route('/healthz', methods=["GET"])
def health_check():
    return "Health", 200


@app.route('/')
def csv_page():
    return render_template('csvPage.html'), 200


@app.route('/json')
def json_page():
    return render_template('jsonPage.html'), 200


if __name__ == '__main__':
    from waitress import serve
    serve(app, port=80, host='0.0.0.0')
