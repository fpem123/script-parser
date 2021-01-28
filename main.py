'''
    Name: app.py
    Writer: Hoseop Lee, Ainizer
    Rule: Flask app
    update: 21.01.28
'''
from flask import Flask, request, jsonify, render_template, send_file

from queue import Queue, Empty
from threading import Thread
from werkzeug.utils import secure_filename
import time
import csv
import os
import io

app = Flask(__name__)

requests_queue = Queue()
BATCH_SIZE = 1
CHECK_INTERVAL = 0.1

# csv 파싱 길이제한 늘림
csv.field_size_limit(100000000)

UPLOAD_FOLDER = './csv_data/upload'
RESULT_FOLDER = './csv_data/result'

# make dir
if not os.path.isdir('./csv_data'):
    os.mkdir('./csv_data')

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
                if len(requests['input']) == 1:
                    requests["output"] = heading_parser(requests['input'][0])
                elif len(requests['input']) == 3:
                    requests["output"] = script_parser(requests['input'][0], requests['input'][1], requests['input'][2])


handler = Thread(target=handle_requests_by_batch).start()


# CSV 파일의 meta 정보를 파싱
def heading_parser(csv_file):
    try:
        # 입력받은 파일 저장
        filename = secure_filename(csv_file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        csv_file.save(input_path)

        with open(input_path, 'r', encoding='utf-8-sig') as f:
            rdr = csv.reader(f)

            csv_headings = next(rdr)    # 컬럼 정보
            first_line = next(rdr)      # 첫째 줄 샘플

            result = [csv_headings, first_line]

        os.remove(input_path)

        return result
    except:
        return jsonify({'message': 'Parsing error'}), 400


# csv 파일의 이름 인덱스와 대사 인덱스를 받아와서 스크립트 파일을 만듬
def script_parser(csv_file, name_idx, dialog_idx):
    try:
        # 입력받은 파일 저장
        filename = secure_filename(csv_file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        csv_file.save(input_path)

        with open(input_path, 'r', encoding='utf-8-sig') as f:
            rdr = csv.reader(f)
            filename = filename.split('.')[0] + '.txt'
            result_path = os.path.join(RESULT_FOLDER, filename)

            with open(result_path, 'w', encoding='utf-8') as r:

                for idx, line in enumerate(rdr):
                    if idx == 0:
                        pass
                    else:
                        # 이름이 없으면 Narrator 로 셋팅
                        who = " ".join(line[name_idx].split()) if line[name_idx] else 'Narrator'
                        dialog = " ".join(line[dialog_idx].split())

                        r.write(who + ': ' + dialog + '\n')

        # 바이너리 정보로 전송하기 위함
        with open(result_path, 'rb') as r:
            data = r.read()

        # 보안을 위한 정보 삭제
        os.remove(input_path)
        os.remove(result_path)

        # heading_parser 와 다른 형태로 전송할 것이므로 구분을 위해 fake 를 추가함
        return io.BytesIO(data), filename, 'fake'
    except Exception:
        return jsonify({'messege': 'Making error'})


@app.route('/<types>', methods=['POST'])
def csv_req(types):
    try:
        if types not in ['heading', 'script']:
            return jsonify({'message': 'Error. Wrong types'}), 400

        if requests_queue.qsize() > BATCH_SIZE:
            return jsonify({'Error': 'Too Many Requests'}), 429

        args = []
        csv_file = request.files['csv_file']
        args.append(csv_file)

        if types == 'script':
            name = int(request.form['name'])
            dialog = int(request.form['dialog'])

            args.append(name)
            args.append(dialog)

    except Exception:
        return jsonify({'message': 'Request Error.'}), 400

    req = {"input": args}
    requests_queue.put(req)

    while 'output' not in req:
        time.sleep(CHECK_INTERVAL)

    result = req['output']

    if len(result) == 2:
        return jsonify(result), 200
    elif len(result) == 3:
        return send_file(result[0], mimetype='text/plain', attachment_filename=result[1]), 200


##
# Sever health checking page.
@app.route('/healthz', methods=["GET"])
def health_check():
    return "Health", 200


@app.route('/')
def main():
    return render_template('main.html'), 200


if __name__ == '__main__':
    from waitress import serve
    serve(app, port=80, host='0.0.0.0')
